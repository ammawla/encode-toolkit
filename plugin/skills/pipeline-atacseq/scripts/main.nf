#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ENCODE ATAC-seq Pipeline — Nextflow DSL2
// FASTQ -> QC -> Bowtie2 -> Tn5 Shift -> Filter -> Peaks -> IDR -> Signal

params.reads       = null
params.genome      = 'GRCh38'
params.outdir      = 'results'
params.single_end  = false
params.skip_idr    = false
params.blacklist   = null
params.chrom_sizes = null
params.mito_name   = 'chrM'
params.nfr_max     = 150
params.tss_bed     = null

def genome_map = [
    'GRCh38': [
        index:     'GRCh38_bowtie2_index',
        blacklist: 'https://github.com/Boyle-Lab/Blacklist/raw/master/lists/hg38-blacklist.v2.bed.gz',
        gsize:     'hs'
    ],
    'mm10': [
        index:     'mm10_bowtie2_index',
        blacklist: 'https://github.com/Boyle-Lab/Blacklist/raw/master/lists/mm10-blacklist.v2.bed.gz',
        gsize:     'mm'
    ]
]

gsize     = genome_map[params.genome].gsize
blacklist = params.blacklist ?: genome_map[params.genome].blacklist

process FASTQC {
    tag "$sample_id"
    publishDir "${params.outdir}/fastqc", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)

    output:
    path("*.{html,zip}"), emit: reports

    script:
    """
    fastqc -t ${task.cpus} --outdir . ${reads}
    """
}

process TRIM_GALORE {
    tag "$sample_id"
    publishDir "${params.outdir}/trimmed", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)

    output:
    tuple val(sample_id), path("*{val_1.fq.gz,val_2.fq.gz,trimmed.fq.gz}"), emit: trimmed
    path("*trimming_report.txt"),                                             emit: log

    script:
    if (params.single_end)
        """
        trim_galore --nextera --quality 20 --length 20 --fastqc --cores ${task.cpus} ${reads}
        """
    else
        """
        trim_galore --paired --nextera --quality 20 --length 20 --fastqc --cores ${task.cpus} ${reads[0]} ${reads[1]}
        """
}

process BOWTIE2_ALIGN {
    tag "$sample_id"
    publishDir "${params.outdir}/aligned", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)
    path(genome_index)

    output:
    tuple val(sample_id), path("${sample_id}.bam"), path("${sample_id}.bam.bai"), emit: bam
    path("${sample_id}.flagstat.txt"),                                              emit: flagstat
    path("${sample_id}.bowtie2.log"),                                               emit: log

    script:
    def input_reads = params.single_end ? "-U ${reads}" : "-1 ${reads[0]} -2 ${reads[1]}"
    """
    bowtie2 --very-sensitive -X 2000 --no-mixed --no-discordant \\
      --threads ${task.cpus} -x ${genome_index}/${params.genome} \\
      ${input_reads} 2> ${sample_id}.bowtie2.log | \\
      samtools view -@ ${task.cpus} -bS -q 30 -f 2 - | \\
      samtools sort -@ ${task.cpus} -m 4G -o ${sample_id}.bam -
    samtools index ${sample_id}.bam
    samtools flagstat ${sample_id}.bam > ${sample_id}.flagstat.txt
    """
}

process MITO_FILTER {
    tag "$sample_id"

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    tuple val(sample_id), path("${sample_id}.no_mito.bam"), emit: bam
    path("${sample_id}.mito_stats.txt"),                     emit: stats

    script:
    """
    # Calculate mito fraction
    TOTAL=\$(samtools view -c ${bam})
    MITO=\$(samtools view -c ${bam} ${params.mito_name})
    echo "total_reads=\$TOTAL mito_reads=\$MITO mito_frac=\$(echo "scale=4; \$MITO/\$TOTAL" | bc)" > ${sample_id}.mito_stats.txt

    # Remove mitochondrial reads
    samtools view -@ ${task.cpus} -b ${bam} \$(samtools idxstats ${bam} | \\
      awk '\$1 != "${params.mito_name}" && \$1 != "*" {print \$1}' | tr '\\n' ' ') > ${sample_id}.no_mito.bam
    """
}

process MARK_DUPLICATES {
    tag "$sample_id"
    publishDir "${params.outdir}/filtered", mode: 'copy', pattern: '*.metrics.txt'

    input:
    tuple val(sample_id), path(bam)

    output:
    tuple val(sample_id), path("${sample_id}.dedup.bam"), emit: bam
    path("${sample_id}.dup_metrics.txt"),                  emit: metrics

    script:
    """
    samtools sort -@ ${task.cpus} -o sorted.bam ${bam}
    picard MarkDuplicates \\
      INPUT=sorted.bam OUTPUT=${sample_id}.dedup.bam \\
      METRICS_FILE=${sample_id}.dup_metrics.txt \\
      REMOVE_DUPLICATES=true VALIDATION_STRINGENCY=LENIENT
    samtools index ${sample_id}.dedup.bam
    """
}

process TN5_SHIFT {
    tag "$sample_id"
    publishDir "${params.outdir}/filtered/shifted", mode: 'copy'

    input:
    tuple val(sample_id), path(bam)

    output:
    tuple val(sample_id), path("${sample_id}.shifted.bam"), path("${sample_id}.shifted.bam.bai"), emit: bam

    script:
    """
    alignmentSieve --bam ${bam} --outFile shifted_unsorted.bam \\
      --ATACshift --numberOfProcessors ${task.cpus}
    samtools sort -@ ${task.cpus} -o ${sample_id}.shifted.bam shifted_unsorted.bam
    samtools index ${sample_id}.shifted.bam
    """
}

process BLACKLIST_FILTER {
    tag "$sample_id"
    publishDir "${params.outdir}/filtered", mode: 'copy'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path(blacklist_bed)

    output:
    tuple val(sample_id), path("${sample_id}.final.bam"), path("${sample_id}.final.bam.bai"), emit: bam
    path("${sample_id}.final.flagstat.txt"),                                                    emit: flagstat

    script:
    """
    bedtools intersect -v -abam ${bam} -b ${blacklist_bed} > ${sample_id}.final.bam
    samtools index ${sample_id}.final.bam
    samtools flagstat ${sample_id}.final.bam > ${sample_id}.final.flagstat.txt
    """
}

process NFR_SELECTION {
    tag "$sample_id"
    publishDir "${params.outdir}/filtered/nfr", mode: 'copy'

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    tuple val(sample_id), path("${sample_id}.nfr.bam"), path("${sample_id}.nfr.bam.bai"), emit: nfr
    tuple val(sample_id), path("${sample_id}.mononuc.bam"),                                emit: mononuc

    script:
    """
    alignmentSieve --bam ${bam} --outFile nfr_unsorted.bam \\
      --maxFragmentLength ${params.nfr_max} --numberOfProcessors ${task.cpus}
    samtools sort -@ ${task.cpus} -o ${sample_id}.nfr.bam nfr_unsorted.bam
    samtools index ${sample_id}.nfr.bam

    alignmentSieve --bam ${bam} --outFile mononuc_unsorted.bam \\
      --minFragmentLength ${params.nfr_max} --maxFragmentLength 300 --numberOfProcessors ${task.cpus}
    samtools sort -@ ${task.cpus} -o ${sample_id}.mononuc.bam mononuc_unsorted.bam
    """
}

process MACS2_CALLPEAK {
    tag "$sample_id"
    publishDir "${params.outdir}/peaks/narrow", mode: 'copy'

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    tuple val(sample_id), path("${sample_id}*narrowPeak"), emit: peaks
    path("${sample_id}*.bdg"),                              emit: bdg
    path("${sample_id}*.xls"),                              emit: xls

    script:
    """
    macs2 callpeak -t ${bam} \\
      -f BAMPE -g ${gsize} -n ${sample_id} \\
      --nomodel --keep-dup all --call-summits \\
      --qvalue 0.05 -B
    """
}

process IDR_ANALYSIS {
    tag "idr"
    publishDir "${params.outdir}/peaks/idr", mode: 'copy'

    input:
    path(peak_files)

    output:
    path("idr_peaks.txt"),     emit: peaks
    path("idr_peaks.txt.png"), emit: plot, optional: true

    when:
    !params.skip_idr

    script:
    """
    idr --samples ${peak_files[0]} ${peak_files[1]} \\
      --input-file-type narrowPeak --rank p.value \\
      --output-file idr_peaks.txt --plot --idr-threshold 0.05
    """
}

process SIGNAL_TRACKS {
    tag "$sample_id"
    publishDir "${params.outdir}/signal", mode: 'copy'

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    path("${sample_id}.signal.bw"), emit: bw

    script:
    """
    bamCoverage -b ${bam} -o ${sample_id}.signal.bw \\
      --normalizeUsing RPKM --binSize 10 \\
      --numberOfProcessors ${task.cpus} --extendReads
    """
}

process MULTIQC {
    publishDir "${params.outdir}/qc/multiqc", mode: 'copy'

    input:
    path('*')

    output:
    path("multiqc_report.html"), emit: report
    path("multiqc_data"),        emit: data

    script:
    """
    multiqc . -o . -f
    """
}

workflow {
    ch_reads  = Channel.fromFilePairs(params.reads, size: params.single_end ? 1 : 2)
    ch_genome = Channel.fromPath(genome_map[params.genome].index, type: 'dir')
    ch_black  = Channel.fromPath(blacklist)

    // Stage 1: QC and Trimming
    FASTQC(ch_reads)
    TRIM_GALORE(ch_reads)

    // Stage 2: Alignment (Bowtie2)
    BOWTIE2_ALIGN(TRIM_GALORE.out.trimmed, ch_genome.collect())

    // Stage 3: Tn5 Shift and Filtering
    MITO_FILTER(BOWTIE2_ALIGN.out.bam)
    MARK_DUPLICATES(MITO_FILTER.out.bam)
    TN5_SHIFT(MARK_DUPLICATES.out.bam)
    BLACKLIST_FILTER(TN5_SHIFT.out.bam, ch_black.collect())
    NFR_SELECTION(BLACKLIST_FILTER.out.bam)

    // Stage 4: Peak Calling on NFR fragments
    MACS2_CALLPEAK(NFR_SELECTION.out.nfr)

    // IDR (optional, with 2+ replicates)
    if (!params.skip_idr) {
        ch_peaks = MACS2_CALLPEAK.out.peaks.map { it[1] }.collect()
        IDR_ANALYSIS(ch_peaks)
    }

    // Stage 5: Signal Tracks and QC
    SIGNAL_TRACKS(BLACKLIST_FILTER.out.bam)

    // MultiQC
    ch_multiqc = FASTQC.out.reports
        .mix(TRIM_GALORE.out.log)
        .mix(BOWTIE2_ALIGN.out.log)
        .mix(MITO_FILTER.out.stats)
        .mix(MARK_DUPLICATES.out.metrics)
        .mix(BLACKLIST_FILTER.out.flagstat)
        .collect()
    MULTIQC(ch_multiqc)
}
