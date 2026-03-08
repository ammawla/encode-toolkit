#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ============================================================================
// ENCODE Hi-C Pipeline — FASTQ to Contact Matrices and Loops
// Tools: BWA-MEM, pairtools, Juicer, cooler, HiCCUPS
// ============================================================================

params.reads            = null
params.bwa_index        = null
params.chrom_sizes      = null
params.restriction_site = 'GATC'
params.outdir           = './results'
params.resolutions      = '1000,5000,10000,25000,50000,100000,250000,500000,1000000'
params.min_mapq         = 30
params.assembly         = 'hg38'

if (!params.reads)       { error "Missing required parameter: --reads" }
if (!params.bwa_index)   { error "Missing required parameter: --bwa_index" }
if (!params.chrom_sizes) { error "Missing required parameter: --chrom_sizes" }

// ---- Channels ----
Channel
    .fromFilePairs(params.reads, checkIfExists: true)
    .set { ch_reads }

ch_bwa_index   = Channel.fromPath("${params.bwa_index}*", checkIfExists: true).collect()
ch_chrom_sizes = Channel.fromPath(params.chrom_sizes, checkIfExists: true)

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

process BWA_ALIGN {
    tag "${sample_id}"
    publishDir "${params.outdir}/alignment", mode: 'copy'
    cpus 8
    memory '16 GB'

    input:
    tuple val(sample_id), path(reads)
    path bwa_idx

    output:
    tuple val(sample_id), path("${sample_id}.paired.bam"), emit: bam

    script:
    def idx_base = params.bwa_index
    """
    bwa mem -t ${task.cpus} -SP5M \\
        ${idx_base} \\
        ${reads[0]} ${reads[1]} \\
        | samtools view -@ 4 -bhS - \\
        > ${sample_id}.paired.bam
    """
}

process PAIRTOOLS_PARSE_SORT {
    tag "${sample_id}"
    cpus 4
    memory '16 GB'

    input:
    tuple val(sample_id), path(bam)
    path chrom_sizes

    output:
    tuple val(sample_id), path("${sample_id}.sorted.pairs.gz"), emit: pairs
    path("${sample_id}.parse_stats.txt"), emit: stats

    script:
    """
    pairtools parse \\
        --chroms-path ${chrom_sizes} \\
        --min-mapq ${params.min_mapq} \\
        --walks-policy mask \\
        --max-inter-align-gap 30 \\
        --nproc-in ${task.cpus} \\
        --nproc-out ${task.cpus} \\
        --output-stats ${sample_id}.parse_stats.txt \\
        ${bam} \\
        | pairtools sort \\
            --nproc ${task.cpus} \\
            --tmpdir \$PWD/tmp \\
            -o ${sample_id}.sorted.pairs.gz
    """
}

process PAIRTOOLS_DEDUP {
    tag "${sample_id}"
    publishDir "${params.outdir}/pairs", mode: 'copy'
    cpus 4
    memory '16 GB'

    input:
    tuple val(sample_id), path(pairs)

    output:
    tuple val(sample_id), path("${sample_id}.dedup.pairs.gz"), emit: pairs
    path("${sample_id}.dedup_stats.txt"), emit: stats

    script:
    """
    pairtools dedup \\
        --nproc-in ${task.cpus} \\
        --nproc-out ${task.cpus} \\
        --mark-dups \\
        --output-stats ${sample_id}.dedup_stats.txt \\
        -o ${sample_id}.dedup.pairs.gz \\
        ${pairs}
    """
}

process PAIRTOOLS_SELECT {
    tag "${sample_id}"
    cpus 2
    memory '8 GB'

    input:
    tuple val(sample_id), path(pairs)

    output:
    tuple val(sample_id), path("${sample_id}.valid.pairs.gz"), emit: pairs
    path("${sample_id}.pair_stats.txt"), emit: stats

    script:
    """
    pairtools select \\
        '(pair_type == "UU")' \\
        ${pairs} \\
        -o ${sample_id}.valid.pairs.gz

    pairtools stats \\
        ${sample_id}.valid.pairs.gz \\
        -o ${sample_id}.pair_stats.txt
    """
}

process JUICER_HIC {
    tag "${sample_id}"
    publishDir "${params.outdir}/matrices", mode: 'copy'
    cpus 4
    memory '64 GB'

    input:
    tuple val(sample_id), path(pairs)
    path chrom_sizes

    output:
    tuple val(sample_id), path("${sample_id}.hic"), emit: hic

    script:
    """
    # Convert to Juicer medium format
    zcat ${pairs} | awk 'BEGIN{OFS="\\t"} !/^#/ {
        s1 = (\$6 == "+") ? 0 : 16;
        s2 = (\$7 == "+") ? 0 : 16;
        print s1, \$2, \$3, 0, s2, \$4, \$5, 1
    }' > juicer_medium.txt

    java -Xmx${task.memory.toGiga()}g -jar /opt/juicer_tools.jar pre \\
        --threads ${task.cpus} \\
        -r ${params.resolutions} \\
        -k KR,VC,VC_SQRT \\
        juicer_medium.txt \\
        ${sample_id}.hic \\
        ${chrom_sizes}

    rm juicer_medium.txt
    """
}

process COOLER_MCOOL {
    tag "${sample_id}"
    publishDir "${params.outdir}/matrices", mode: 'copy'
    cpus 4
    memory '16 GB'

    input:
    tuple val(sample_id), path(pairs)
    path chrom_sizes

    output:
    tuple val(sample_id), path("${sample_id}.mcool"), emit: mcool

    script:
    """
    cooler cload pairs \\
        --chrom1 2 --pos1 3 --chrom2 4 --pos2 5 \\
        --assembly ${params.assembly} \\
        ${chrom_sizes}:1000 \\
        ${pairs} \\
        ${sample_id}_1kb.cool

    cooler zoomify \\
        --balance \\
        --resolutions ${params.resolutions} \\
        --nproc ${task.cpus} \\
        ${sample_id}_1kb.cool \\
        -o ${sample_id}.mcool
    """
}

process HICCUPS {
    tag "${sample_id}"
    publishDir "${params.outdir}/loops", mode: 'copy'
    cpus 4
    memory '16 GB'

    input:
    tuple val(sample_id), path(hic)

    output:
    path("${sample_id}.hiccups_loops.bedpe"), emit: loops

    script:
    """
    java -Xmx${task.memory.toGiga()}g -jar /opt/juicer_tools.jar hiccups \\
        --threads ${task.cpus} \\
        -r 5000,10000,25000 \\
        -f 0.1,0.1,0.1 \\
        -p 4,2,1 \\
        -i 7,5,3 \\
        -d 20000,20000,50000 \\
        ${hic} \\
        hiccups_out/

    cp hiccups_out/merged_loops.bedpe ${sample_id}.hiccups_loops.bedpe
    """
}

process CONTACT_STATS {
    tag "${sample_id}"
    publishDir "${params.outdir}/qc", mode: 'copy'
    cpus 1
    memory '4 GB'

    input:
    tuple val(sample_id), path(pairs)

    output:
    path("${sample_id}.contact_stats.txt"), emit: stats

    script:
    """
    pairtools stats ${pairs} -o ${sample_id}.contact_stats.txt
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
    multiqc --title "ENCODE Hi-C Pipeline" --force .
    """
}

// ---- Workflow ----

workflow {
    FASTQC_RAW(ch_reads)
    BWA_ALIGN(ch_reads, ch_bwa_index)
    PAIRTOOLS_PARSE_SORT(BWA_ALIGN.out.bam, ch_chrom_sizes.collect())
    PAIRTOOLS_DEDUP(PAIRTOOLS_PARSE_SORT.out.pairs)
    PAIRTOOLS_SELECT(PAIRTOOLS_DEDUP.out.pairs)

    JUICER_HIC(PAIRTOOLS_SELECT.out.pairs, ch_chrom_sizes.collect())
    COOLER_MCOOL(PAIRTOOLS_SELECT.out.pairs, ch_chrom_sizes.collect())
    HICCUPS(JUICER_HIC.out.hic)
    CONTACT_STATS(PAIRTOOLS_SELECT.out.pairs)

    ch_multiqc = FASTQC_RAW.out.reports
        .mix(PAIRTOOLS_PARSE_SORT.out.stats)
        .mix(PAIRTOOLS_DEDUP.out.stats)
        .mix(PAIRTOOLS_SELECT.out.stats)
        .collect()

    MULTIQC(ch_multiqc)
}
