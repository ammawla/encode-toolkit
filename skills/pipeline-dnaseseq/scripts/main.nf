#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ============================================================================
// ENCODE DNase-seq Pipeline — FASTQ to Hotspots and Footprints
// Tools: BWA-MEM, Hotspot2, HINT-ATAC
// ============================================================================

params.reads          = null
params.bwa_index      = null
params.chrom_sizes    = null
params.hotspot_index  = null
params.blacklist      = null
params.outdir         = './results'
params.fdr            = 0.05
params.skip_footprint = false
params.motif_db       = null

if (!params.reads)         { error "Missing required parameter: --reads" }
if (!params.bwa_index)     { error "Missing required parameter: --bwa_index" }
if (!params.chrom_sizes)   { error "Missing required parameter: --chrom_sizes" }
if (!params.hotspot_index) { error "Missing required parameter: --hotspot_index" }
if (!params.blacklist)     { error "Missing required parameter: --blacklist" }

// ---- Channels ----
Channel
    .fromFilePairs(params.reads, checkIfExists: true)
    .set { ch_reads }

ch_bwa_index      = Channel.fromPath("${params.bwa_index}*", checkIfExists: true).collect()
ch_chrom_sizes    = Channel.fromPath(params.chrom_sizes, checkIfExists: true)
ch_hotspot_index  = Channel.fromPath(params.hotspot_index, checkIfExists: true)
ch_blacklist      = Channel.fromPath(params.blacklist, checkIfExists: true)

// ---- Processes ----

process FASTQC_RAW {
    tag "${sample_id}"
    publishDir "${params.outdir}/fastqc", mode: 'copy'
    cpus 2
    memory '4 GB'

    input:
    tuple val(sample_id), path(reads)

    output:
    path("*.{html,zip}"), emit: reports

    script:
    """
    fastqc --threads ${task.cpus} --outdir . ${reads}
    """
}

process TRIM_GALORE {
    tag "${sample_id}"
    publishDir "${params.outdir}/trim_galore", mode: 'copy'
    cpus 4
    memory '4 GB'

    input:
    tuple val(sample_id), path(reads)

    output:
    tuple val(sample_id), path("*_val_{1,2}.fq.gz"), emit: trimmed
    path("*_trimming_report.txt"), emit: reports

    script:
    """
    trim_galore \\
        --paired \\
        --quality 20 \\
        --phred33 \\
        --length 20 \\
        --cores ${task.cpus} \\
        --fastqc \\
        ${reads[0]} ${reads[1]}
    """
}

process BWA_ALIGN {
    tag "${sample_id}"
    cpus 8
    memory '16 GB'

    input:
    tuple val(sample_id), path(reads)
    path bwa_idx

    output:
    tuple val(sample_id), path("${sample_id}.sorted.bam"), path("${sample_id}.sorted.bam.bai"), emit: bam

    script:
    def idx_base = params.bwa_index
    """
    bwa mem -t ${task.cpus} -M \\
        ${idx_base} \\
        ${reads[0]} ${reads[1]} \\
        | samtools view -@ 4 -bS - \\
        | samtools sort -@ 4 -o ${sample_id}.sorted.bam

    samtools index ${sample_id}.sorted.bam
    """
}

process FILTER_DEDUP {
    tag "${sample_id}"
    publishDir "${params.outdir}/alignment", mode: 'copy'
    cpus 4
    memory '8 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path blacklist

    output:
    tuple val(sample_id), path("${sample_id}.filtered.bam"), path("${sample_id}.filtered.bam.bai"), emit: bam
    path("${sample_id}.dup_metrics.txt"), emit: dup_metrics
    path("${sample_id}.flagstat.txt"), emit: flagstat

    script:
    """
    # Remove chrM and filter quality
    samtools idxstats ${bam} | \\
        awk '\$1 != "chrM" && \$1 != "*" {print \$1}' > chroms.txt

    samtools view -b -h -q 30 -F 1804 -f 2 \\
        ${bam} \$(cat chroms.txt | tr '\\n' ' ') \\
        | samtools sort -@ ${task.cpus} -o nuclear.bam

    # Mark and remove duplicates
    picard MarkDuplicates \\
        INPUT=nuclear.bam \\
        OUTPUT=dedup.bam \\
        METRICS_FILE=${sample_id}.dup_metrics.txt \\
        REMOVE_DUPLICATES=true \\
        VALIDATION_STRINGENCY=LENIENT \\
        ASSUME_SORTED=true

    # Remove blacklist regions
    bedtools intersect \\
        -a dedup.bam \\
        -b ${blacklist} \\
        -v \\
        > ${sample_id}.filtered.bam

    samtools index ${sample_id}.filtered.bam
    samtools flagstat ${sample_id}.filtered.bam > ${sample_id}.flagstat.txt

    rm nuclear.bam dedup.bam
    """
}

process HOTSPOT2 {
    tag "${sample_id}"
    publishDir "${params.outdir}/hotspots", mode: 'copy'
    cpus 4
    memory '8 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path chrom_sizes
    path hotspot_index

    output:
    tuple val(sample_id), path("${sample_id}.hotspots.fdr*.bed"), emit: hotspots
    tuple val(sample_id), path("${sample_id}.peaks.narrowPeak"), emit: peaks
    path("${sample_id}.SPOT.txt"), emit: spot
    path("${sample_id}.allcalls.bed"), emit: allcalls

    script:
    """
    # Run Hotspot2
    hotspot2.sh \\
        -c ${chrom_sizes} \\
        -M ${hotspot_index}/*.mappable_only.bed \\
        -f ${params.fdr} \\
        -F 0.05 \\
        -p "DNase-seq" \\
        -s ${bam} \\
        -o hotspot2_out/

    # Convert starch to BED
    unstarch hotspot2_out/*.hotspots.fdr*.starch > ${sample_id}.hotspots.fdr${params.fdr}.bed
    cp hotspot2_out/*.peaks.narrowPeak ${sample_id}.peaks.narrowPeak
    cp hotspot2_out/*.SPOT.txt ${sample_id}.SPOT.txt
    unstarch hotspot2_out/*.allcalls.starch > ${sample_id}.allcalls.bed
    """
}

process SIGNAL_TRACK {
    tag "${sample_id}"
    publishDir "${params.outdir}/hotspots", mode: 'copy'
    cpus 2
    memory '4 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path chrom_sizes

    output:
    path("${sample_id}.density.bw"), emit: bigwig

    script:
    """
    # Generate RPM-normalized signal
    total=\$(samtools view -c -F 1804 -f 2 ${bam})
    scale=\$(echo "scale=10; 1000000 / \$total" | bc)

    bedtools genomecov \\
        -ibam ${bam} \\
        -bg \\
        -pc \\
        -g ${chrom_sizes} \\
        | awk -v s=\$scale 'BEGIN{OFS="\\t"} {\$4=\$4*s; print}' \\
        | sort -k1,1 -k2,2n \\
        > ${sample_id}_rpm.bedGraph

    bedGraphToBigWig ${sample_id}_rpm.bedGraph ${chrom_sizes} ${sample_id}.density.bw
    """
}

process FOOTPRINTING {
    tag "${sample_id}"
    publishDir "${params.outdir}/footprints", mode: 'copy'
    cpus 4
    memory '8 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)
    tuple val(sample_id2), path(peaks)

    output:
    path("${sample_id}.footprints.bed"), emit: footprints

    when:
    !params.skip_footprint

    script:
    """
    rgt-hint footprinting \\
        --dnase-seq \\
        --paired-end \\
        --organism hg38 \\
        --output-location fp_out/ \\
        --output-prefix ${sample_id} \\
        ${bam} \\
        ${peaks}

    cp fp_out/${sample_id}.bed ${sample_id}.footprints.bed
    """
}

process INSERT_SIZES {
    tag "${sample_id}"
    publishDir "${params.outdir}/qc", mode: 'copy'
    cpus 1
    memory '4 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    path("${sample_id}.insert_sizes.txt"), emit: metrics

    script:
    """
    picard CollectInsertSizeMetrics \\
        INPUT=${bam} \\
        OUTPUT=${sample_id}.insert_sizes.txt \\
        HISTOGRAM_FILE=${sample_id}.insert_hist.pdf \\
        MINIMUM_PCT=0.05 \\
        VALIDATION_STRINGENCY=LENIENT
    """
}

process MULTIQC {
    publishDir "${params.outdir}/multiqc", mode: 'copy'
    cpus 1
    memory '4 GB'

    input:
    path('*')

    output:
    path("multiqc_report.html"), emit: report

    script:
    """
    multiqc --title "ENCODE DNase-seq Pipeline" --force .
    """
}

// ---- Workflow ----

workflow {
    FASTQC_RAW(ch_reads)
    TRIM_GALORE(ch_reads)
    BWA_ALIGN(TRIM_GALORE.out.trimmed, ch_bwa_index)
    FILTER_DEDUP(BWA_ALIGN.out.bam, ch_blacklist.collect())
    HOTSPOT2(FILTER_DEDUP.out.bam, ch_chrom_sizes.collect(), ch_hotspot_index.collect())
    SIGNAL_TRACK(FILTER_DEDUP.out.bam, ch_chrom_sizes.collect())
    INSERT_SIZES(FILTER_DEDUP.out.bam)

    if (!params.skip_footprint) {
        FOOTPRINTING(FILTER_DEDUP.out.bam, HOTSPOT2.out.peaks)
    }

    ch_multiqc = FASTQC_RAW.out.reports
        .mix(TRIM_GALORE.out.reports)
        .mix(FILTER_DEDUP.out.flagstat)
        .mix(FILTER_DEDUP.out.dup_metrics)
        .mix(HOTSPOT2.out.spot)
        .collect()

    MULTIQC(ch_multiqc)
}
