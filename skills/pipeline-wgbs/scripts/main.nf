#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ============================================================================
// ENCODE WGBS Pipeline — FASTQ to bedMethyl
// Tools: Trim Galore, Bismark, MethylDackel
// ============================================================================

params.reads       = null
params.genome_dir  = null
params.outdir      = './results'
params.aligner     = 'bismark'    // 'bismark' or 'bwameth'
params.min_coverage = 5
params.no_overlap  = true
params.lambda_genome = null
params.skip_dedup  = false

if (!params.reads)      { error "Missing required parameter: --reads" }
if (!params.genome_dir) { error "Missing required parameter: --genome_dir" }

// ---- Channels ----
Channel
    .fromFilePairs(params.reads, checkIfExists: true)
    .set { ch_reads }

ch_genome = Channel.fromPath(params.genome_dir, checkIfExists: true)

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
        --length 36 \\
        --cores ${task.cpus} \\
        --clip_R2 10 \\
        --three_prime_clip_R1 1 \\
        --fastqc \\
        ${reads[0]} ${reads[1]}
    """
}

process BISMARK_ALIGN {
    tag "${sample_id}"
    publishDir "${params.outdir}/bismark/alignments", mode: 'copy'
    cpus 8
    memory '48 GB'

    input:
    tuple val(sample_id), path(reads)
    path genome_dir

    output:
    tuple val(sample_id), path("*.bam"), emit: bam
    path("*_report.txt"), emit: report

    script:
    """
    bismark \\
        --genome ${genome_dir} \\
        --bowtie2 \\
        --parallel 4 \\
        --score_min L,0,-0.2 \\
        --no_mixed \\
        --no_discordant \\
        --maxins 1000 \\
        --temp_dir \$PWD/tmp \\
        -1 ${reads[0]} \\
        -2 ${reads[1]}
    """
}

process DEDUPLICATE {
    tag "${sample_id}"
    publishDir "${params.outdir}/bismark/dedup_reports", mode: 'copy', pattern: '*.txt'
    cpus 2
    memory '16 GB'

    input:
    tuple val(sample_id), path(bam)

    output:
    tuple val(sample_id), path("*.deduplicated.bam"), emit: bam
    path("*.deduplication_report.txt"), emit: report

    when:
    !params.skip_dedup

    script:
    """
    deduplicate_bismark --bam --paired ${bam}
    """
}

process SAMTOOLS_SORT_INDEX {
    tag "${sample_id}"
    cpus 4
    memory '8 GB'

    input:
    tuple val(sample_id), path(bam)

    output:
    tuple val(sample_id), path("${sample_id}.sorted.bam"), path("${sample_id}.sorted.bam.bai"), emit: bam

    script:
    """
    samtools sort -@ ${task.cpus} -o ${sample_id}.sorted.bam ${bam}
    samtools index ${sample_id}.sorted.bam
    """
}

process METHYLDACKEL_MBIAS {
    tag "${sample_id}"
    publishDir "${params.outdir}/bismark/mbias", mode: 'copy'
    cpus 2
    memory '8 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path genome_dir

    output:
    path("*.svg"), emit: plots
    path("*.txt"), emit: report

    script:
    def genome_fa = "${genome_dir}/*.fa"
    """
    GENOME_FA=\$(ls ${genome_dir}/*.fa | head -1)
    MethylDackel mbias \\
        --CHG --CHH \\
        \$GENOME_FA \\
        ${bam} \\
        ${sample_id}_mbias > ${sample_id}_mbias_report.txt
    """
}

process METHYLDACKEL_EXTRACT {
    tag "${sample_id}"
    publishDir "${params.outdir}/bismark/methylation", mode: 'copy'
    cpus 4
    memory '8 GB'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path genome_dir

    output:
    tuple val(sample_id), path("*.bedGraph"), emit: bedgraph
    tuple val(sample_id), path("*.bedMethyl.gz"), emit: bedmethyl

    script:
    def merge = params.no_overlap ? '--mergeContext' : ''
    """
    GENOME_FA=\$(ls ${genome_dir}/*.fa | head -1)
    MethylDackel extract \\
        ${merge} \\
        --minDepth ${params.min_coverage} \\
        --maxDepth 8000 \\
        --nOT 0,0,0,10 \\
        --nOB 0,10,0,0 \\
        --CHG --CHH \\
        --opref ${sample_id} \\
        \$GENOME_FA \\
        ${bam}

    # Convert CpG bedGraph to bedMethyl
    awk 'BEGIN {OFS="\\t"} {
        cov = \$5 + \$6;
        pct = (\$5 / cov) * 100;
        print \$1, \$2, \$3, ".", int(pct*10), "+", \$2, \$3, "0,0,0", cov, pct
    }' ${sample_id}_CpG.bedGraph \\
        | sort -k1,1 -k2,2n \\
        | bgzip > ${sample_id}.CpG.bedMethyl.gz

    tabix -p bed ${sample_id}.CpG.bedMethyl.gz
    """
}

process COVERAGE_STATS {
    tag "${sample_id}"
    publishDir "${params.outdir}/coverage", mode: 'copy'
    cpus 2
    memory '4 GB'

    input:
    tuple val(sample_id), path(bedgraph)

    output:
    path("${sample_id}.coverage_stats.txt"), emit: stats

    script:
    """
    awk '{
        cov = \$5 + \$6; sum += cov; n++;
        if (cov >= 1)  c1++;
        if (cov >= 5)  c5++;
        if (cov >= 10) c10++
    } END {
        printf "Total CpGs: %d\\n", n;
        printf "Mean coverage: %.1f\\n", sum/n;
        printf "CpGs >=1x: %d (%.1f%%)\\n", c1, c1/n*100;
        printf "CpGs >=5x: %d (%.1f%%)\\n", c5, c5/n*100;
        printf "CpGs >=10x: %d (%.1f%%)\\n", c10, c10/n*100
    }' ${sample_id}_CpG.bedGraph > ${sample_id}.coverage_stats.txt
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
    multiqc --title "ENCODE WGBS Pipeline" --force .
    """
}

// ---- Workflow ----

workflow {
    FASTQC_RAW(ch_reads)
    TRIM_GALORE(ch_reads)

    BISMARK_ALIGN(TRIM_GALORE.out.trimmed, ch_genome.collect())

    if (!params.skip_dedup) {
        DEDUPLICATE(BISMARK_ALIGN.out.bam)
        SAMTOOLS_SORT_INDEX(DEDUPLICATE.out.bam)
    } else {
        SAMTOOLS_SORT_INDEX(BISMARK_ALIGN.out.bam)
    }

    METHYLDACKEL_MBIAS(SAMTOOLS_SORT_INDEX.out.bam, ch_genome.collect())
    METHYLDACKEL_EXTRACT(SAMTOOLS_SORT_INDEX.out.bam, ch_genome.collect())
    COVERAGE_STATS(METHYLDACKEL_EXTRACT.out.bedgraph)

    ch_multiqc = FASTQC_RAW.out.reports
        .mix(TRIM_GALORE.out.reports)
        .mix(BISMARK_ALIGN.out.report)
        .collect()

    MULTIQC(ch_multiqc)
}
