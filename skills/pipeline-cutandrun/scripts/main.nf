#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ============================================================================
// ENCODE CUT&RUN Pipeline — FASTQ to Peaks and Signal Tracks
// Tools: Bowtie2, SEACR, MACS2, deepTools
// ============================================================================

params.reads          = null
params.bowtie2_index  = null
params.spikein_index  = null
params.chrom_sizes    = null
params.blacklist      = null
params.outdir         = './results'
params.seacr_mode     = 'stringent'
params.seacr_norm     = 'norm'
params.control        = null
params.peak_caller    = 'seacr'    // 'seacr', 'macs2', or 'both'
params.skip_spikein   = false

if (!params.reads)         { error "Missing required parameter: --reads" }
if (!params.bowtie2_index) { error "Missing required parameter: --bowtie2_index" }
if (!params.chrom_sizes)   { error "Missing required parameter: --chrom_sizes" }
if (!params.blacklist)     { error "Missing required parameter: --blacklist" }

// ---- Channels ----
Channel
    .fromFilePairs(params.reads, checkIfExists: true)
    .set { ch_reads }

ch_bt2_index    = Channel.fromPath("${params.bowtie2_index}*", checkIfExists: true).collect()
ch_chrom_sizes  = Channel.fromPath(params.chrom_sizes, checkIfExists: true)
ch_blacklist    = Channel.fromPath(params.blacklist, checkIfExists: true)

if (params.spikein_index) {
    ch_spikein_index = Channel.fromPath("${params.spikein_index}*", checkIfExists: true).collect()
}

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
        --nextera \\
        --fastqc \\
        ${reads[0]} ${reads[1]}
    """
}

process BOWTIE2_ALIGN {
    tag "${sample_id}"
    cpus 8
    memory '8 GB'

    input:
    tuple val(sample_id), path(reads)
    path bt2_idx

    output:
    tuple val(sample_id), path("${sample_id}.sorted.bam"), path("${sample_id}.sorted.bam.bai"), emit: bam
    path("${sample_id}.bowtie2.log"), emit: log

    script:
    def idx_prefix = params.bowtie2_index
    """
    bowtie2 \\
        --very-sensitive \\
        --no-mixed \\
        --no-discordant \\
        --dovetail \\
        --phred33 \\
        -I 10 -X 700 \\
        --threads ${task.cpus} \\
        -x ${idx_prefix} \\
        -1 ${reads[0]} \\
        -2 ${reads[1]} \\
        2> ${sample_id}.bowtie2.log \\
        | samtools view -@ 4 -bS - \\
        | samtools sort -@ 4 -o ${sample_id}.sorted.bam

    samtools index ${sample_id}.sorted.bam
    """
}

process SPIKEIN_ALIGN {
    tag "${sample_id}"
    cpus 4
    memory '4 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path spikein_idx

    output:
    tuple val(sample_id), path("${sample_id}.spikein_counts.txt"), emit: counts

    when:
    !params.skip_spikein && params.spikein_index

    script:
    def idx_prefix = params.spikein_index
    """
    # Extract unmapped reads
    samtools view -b -f 12 -F 256 ${bam} | samtools sort -n -@ 2 -o unmapped.bam
    bedtools bamtofastq -i unmapped.bam -fq unmap_R1.fq -fq2 unmap_R2.fq

    # Align to spike-in
    bowtie2 \\
        --very-sensitive \\
        --no-mixed --no-discordant --dovetail \\
        -I 10 -X 700 \\
        --threads ${task.cpus} \\
        -x ${idx_prefix} \\
        -1 unmap_R1.fq -2 unmap_R2.fq \\
        2> spikein.log \\
        | samtools view -bS -q 10 -F 1804 -f 2 - \\
        | samtools sort -o spikein.bam

    spikein_count=\$(samtools view -c spikein.bam)
    echo "${sample_id}\t\${spikein_count}" > ${sample_id}.spikein_counts.txt
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
    # Quality filter
    samtools view -b -h -q 10 -F 1804 -f 2 ${bam} \\
        | samtools sort -@ ${task.cpus} -o qfilt.bam

    # Mark and remove duplicates
    picard MarkDuplicates \\
        INPUT=qfilt.bam \\
        OUTPUT=dedup.bam \\
        METRICS_FILE=${sample_id}.dup_metrics.txt \\
        REMOVE_DUPLICATES=true \\
        VALIDATION_STRINGENCY=LENIENT \\
        ASSUME_SORTED=true

    # Remove blacklist regions
    bedtools intersect -a dedup.bam -b ${blacklist} -v \\
        > ${sample_id}.filtered.bam

    samtools index ${sample_id}.filtered.bam
    samtools flagstat ${sample_id}.filtered.bam > ${sample_id}.flagstat.txt

    rm qfilt.bam dedup.bam
    """
}

process COMPUTE_SCALE_FACTOR {
    publishDir "${params.outdir}/spikein", mode: 'copy'
    cpus 1
    memory '1 GB'

    input:
    path(counts)

    output:
    path("scale_factors.txt"), emit: factors

    when:
    !params.skip_spikein

    script:
    """
    cat ${counts} > all_counts.txt
    min_count=\$(awk '{print \$2}' all_counts.txt | sort -n | head -1)
    awk -v min=\$min_count '{print \$1, \$2, min/\$2}' all_counts.txt > scale_factors.txt
    """
}

process FRAGMENT_BED {
    tag "${sample_id}"
    cpus 2
    memory '4 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    tuple val(sample_id), path("${sample_id}_fragments.bedGraph"), emit: bedgraph

    script:
    """
    bedtools bamtobed -bedpe -i ${bam} \\
        | awk 'BEGIN{OFS="\\t"} {print \$1, \$2, \$6, \$7, \$8, \$9}' \\
        | sort -k1,1 -k2,2n \\
        > fragments.bed

    bedtools genomecov -i fragments.bed -g ${params.chrom_sizes} -bg \\
        | sort -k1,1 -k2,2n > ${sample_id}_fragments.bedGraph
    """
}

process SEACR_PEAKS {
    tag "${sample_id}"
    publishDir "${params.outdir}/peaks", mode: 'copy'
    cpus 2
    memory '4 GB'

    input:
    tuple val(sample_id), path(bedgraph)

    output:
    tuple val(sample_id), path("${sample_id}.seacr.*.bed"), emit: peaks

    when:
    params.peak_caller == 'seacr' || params.peak_caller == 'both'

    script:
    def ctrl = params.control ? "${params.control}" : "0.01"
    """
    # Stringent
    SEACR_1.3.sh ${bedgraph} ${ctrl} ${params.seacr_norm} stringent ${sample_id}.seacr

    # Also run relaxed
    SEACR_1.3.sh ${bedgraph} ${ctrl} ${params.seacr_norm} relaxed ${sample_id}.seacr
    """
}

process MACS2_PEAKS {
    tag "${sample_id}"
    publishDir "${params.outdir}/peaks", mode: 'copy'
    cpus 2
    memory '4 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    tuple val(sample_id), path("${sample_id}.macs2_peaks.narrowPeak"), emit: peaks

    when:
    params.peak_caller == 'macs2' || params.peak_caller == 'both'

    script:
    def ctrl_flag = params.control ? "-c ${params.control}" : ""
    """
    macs2 callpeak \\
        -t ${bam} \\
        ${ctrl_flag} \\
        -f BAMPE \\
        -g hs \\
        -n ${sample_id}.macs2 \\
        --nomodel \\
        --keep-dup all \\
        -q 0.05 \\
        --outdir .

    mv ${sample_id}.macs2_peaks.narrowPeak ${sample_id}.macs2_peaks.narrowPeak
    """
}

process SIGNAL_TRACK {
    tag "${sample_id}"
    publishDir "${params.outdir}/signal", mode: 'copy'
    cpus 4
    memory '8 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    path("${sample_id}.normalized.bw"), emit: bigwig

    script:
    """
    bamCoverage \\
        --bam ${bam} \\
        --outFileName ${sample_id}.normalized.bw \\
        --binSize 10 \\
        --normalizeUsing RPKM \\
        --extendReads \\
        --numberOfProcessors ${task.cpus}
    """
}

process FRAGMENT_SIZES {
    tag "${sample_id}"
    publishDir "${params.outdir}/qc", mode: 'copy'
    cpus 1
    memory '4 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    path("${sample_id}.fragment_sizes.txt"), emit: sizes

    script:
    """
    samtools view -f 2 -F 1804 ${bam} | \\
        awk '{if(\$9 > 0 && \$9 < 1000) print \$9}' | \\
        sort -n | uniq -c | \\
        awk '{print \$2, \$1}' > ${sample_id}.fragment_sizes.txt
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
    multiqc --title "ENCODE CUT&RUN Pipeline" --force .
    """
}

// ---- Workflow ----

workflow {
    FASTQC_RAW(ch_reads)
    TRIM_GALORE(ch_reads)
    BOWTIE2_ALIGN(TRIM_GALORE.out.trimmed, ch_bt2_index)

    if (!params.skip_spikein && params.spikein_index) {
        SPIKEIN_ALIGN(BOWTIE2_ALIGN.out.bam, ch_spikein_index)
        COMPUTE_SCALE_FACTOR(SPIKEIN_ALIGN.out.counts.map{ it[1] }.collect())
    }

    FILTER_DEDUP(BOWTIE2_ALIGN.out.bam, ch_blacklist.collect())
    FRAGMENT_BED(FILTER_DEDUP.out.bam)

    if (params.peak_caller == 'seacr' || params.peak_caller == 'both') {
        SEACR_PEAKS(FRAGMENT_BED.out.bedgraph)
    }
    if (params.peak_caller == 'macs2' || params.peak_caller == 'both') {
        MACS2_PEAKS(FILTER_DEDUP.out.bam)
    }

    SIGNAL_TRACK(FILTER_DEDUP.out.bam)
    FRAGMENT_SIZES(FILTER_DEDUP.out.bam)

    ch_multiqc = FASTQC_RAW.out.reports
        .mix(TRIM_GALORE.out.reports)
        .mix(BOWTIE2_ALIGN.out.log)
        .mix(FILTER_DEDUP.out.flagstat)
        .mix(FILTER_DEDUP.out.dup_metrics)
        .collect()

    MULTIQC(ch_multiqc)
}
