#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ENCODE ChIP-seq Pipeline — Nextflow DSL2
// FASTQ -> QC -> Align -> Filter -> Peaks -> IDR -> Signal

params.reads       = null
params.control     = null
params.genome      = 'GRCh38'
params.peak_type   = 'narrow'
params.outdir      = 'results'
params.single_end  = false
params.skip_idr    = false
params.blacklist   = null
params.chrom_sizes = null

// Genome references map
def genome_map = [
    'GRCh38': [
        fasta:      'https://www.encodeproject.org/files/GRCh38_no_alt_analysis_set_GCA_000001405.15/@@download/GRCh38_no_alt_analysis_set_GCA_000001405.15.fasta.gz',
        blacklist:  'https://github.com/Boyle-Lab/Blacklist/raw/master/lists/hg38-blacklist.v2.bed.gz',
        gsize:      'hs'
    ],
    'mm10': [
        fasta:      'https://www.encodeproject.org/files/mm10_no_alt_analysis_set_ENCODE/@@download/mm10_no_alt_analysis_set_ENCODE.fasta.gz',
        blacklist:  'https://github.com/Boyle-Lab/Blacklist/raw/master/lists/mm10-blacklist.v2.bed.gz',
        gsize:      'mm'
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
        trim_galore --quality 20 --length 36 --fastqc --cores ${task.cpus} ${reads}
        """
    else
        """
        trim_galore --paired --quality 20 --length 36 --fastqc --cores ${task.cpus} ${reads[0]} ${reads[1]}
        """
}

process BWA_MEM {
    tag "$sample_id"
    publishDir "${params.outdir}/aligned", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)
    path(genome_index)

    output:
    tuple val(sample_id), path("${sample_id}.bam"), path("${sample_id}.bam.bai"), emit: bam
    path("${sample_id}.flagstat.txt"),                                              emit: flagstat

    script:
    def input_reads = params.single_end ? "${reads}" : "${reads[0]} ${reads[1]}"
    """
    bwa mem -t ${task.cpus} -M ${genome_index}/${params.genome}.fa ${input_reads} | \\
      samtools view -@ ${task.cpus} -bS -q 30 - | \\
      samtools sort -@ ${task.cpus} -m 4G -o ${sample_id}.bam -
    samtools index ${sample_id}.bam
    samtools flagstat ${sample_id}.bam > ${sample_id}.flagstat.txt
    """
}

process FILTER_SORT {
    tag "$sample_id"

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    tuple val(sample_id), path("${sample_id}.filtered.bam"), emit: bam

    script:
    def flags = params.single_end ? '-F 1028' : '-F 1804'
    """
    samtools view -@ ${task.cpus} -b ${flags} -q 30 ${bam} | \\
      samtools sort -@ ${task.cpus} -o ${sample_id}.filtered.bam -
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
    picard MarkDuplicates \\
      INPUT=${bam} OUTPUT=${sample_id}.dedup.bam \\
      METRICS_FILE=${sample_id}.dup_metrics.txt \\
      REMOVE_DUPLICATES=true VALIDATION_STRINGENCY=LENIENT
    """
}

process BLACKLIST_FILTER {
    tag "$sample_id"
    publishDir "${params.outdir}/filtered", mode: 'copy'

    input:
    tuple val(sample_id), path(bam)
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

process MACS2_CALLPEAK {
    tag "$sample_id"
    publishDir "${params.outdir}/peaks/${params.peak_type}", mode: 'copy'

    input:
    tuple val(sample_id), path(treatment_bam), path(treatment_bai)
    tuple val(control_id), path(control_bam), path(control_bai)

    output:
    tuple val(sample_id), path("${sample_id}*Peak"),    emit: peaks
    path("${sample_id}*.bdg"),                           emit: bdg
    path("${sample_id}*.xls"),                           emit: xls

    script:
    def format_flag = params.single_end ? 'BAM' : 'BAMPE'
    def broad_flags = params.peak_type == 'broad' ? '--broad --broad-cutoff 0.1' : '--call-summits'
    """
    macs2 callpeak \\
      -t ${treatment_bam} -c ${control_bam} \\
      -f ${format_flag} -g ${gsize} -n ${sample_id} \\
      --qvalue 0.05 --nomodel --keep-dup all \\
      ${broad_flags} -B
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
    !params.skip_idr && params.peak_type == 'narrow'

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
    tuple val(sample_id), path(bdg_files)
    path(chrom_sizes)

    output:
    path("${sample_id}.fc.bw"),   emit: fc_bw
    path("${sample_id}.pval.bw"), emit: pval_bw

    script:
    """
    macs2 bdgcmp -t ${sample_id}_treat_pileup.bdg -c ${sample_id}_control_lambda.bdg -o fc.bdg -m FE
    sort -k1,1 -k2,2n fc.bdg > fc.sorted.bdg
    bedGraphToBigWig fc.sorted.bdg ${chrom_sizes} ${sample_id}.fc.bw

    macs2 bdgcmp -t ${sample_id}_treat_pileup.bdg -c ${sample_id}_control_lambda.bdg -o pval.bdg -m ppois
    sort -k1,1 -k2,2n pval.bdg > pval.sorted.bdg
    bedGraphToBigWig pval.sorted.bdg ${chrom_sizes} ${sample_id}.pval.bw
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
    // Input channels
    ch_reads   = Channel.fromFilePairs(params.reads, size: params.single_end ? 1 : 2)
    ch_control = Channel.fromFilePairs(params.control, size: params.single_end ? 1 : 2)
    ch_genome  = Channel.fromPath("${params.genome}_index", type: 'dir')
    ch_black   = Channel.fromPath(blacklist)
    ch_chromsz = Channel.fromPath(params.chrom_sizes ?: "chrom.sizes")

    // Stage 1: QC and Trimming
    FASTQC(ch_reads)
    TRIM_GALORE(ch_reads)

    // Stage 2: Alignment
    BWA_MEM(TRIM_GALORE.out.trimmed, ch_genome.collect())

    // Stage 3: Filtering
    FILTER_SORT(BWA_MEM.out.bam)
    MARK_DUPLICATES(FILTER_SORT.out.bam)
    BLACKLIST_FILTER(MARK_DUPLICATES.out.bam, ch_black.collect())

    // Process control through same filtering
    TRIM_GALORE_CTRL = TRIM_GALORE(ch_control)
    BWA_MEM_CTRL     = BWA_MEM(TRIM_GALORE_CTRL.trimmed, ch_genome.collect())
    FILTER_CTRL      = FILTER_SORT(BWA_MEM_CTRL.bam)
    DEDUP_CTRL       = MARK_DUPLICATES(FILTER_CTRL.bam)
    FINAL_CTRL       = BLACKLIST_FILTER(DEDUP_CTRL.bam, ch_black.collect())

    // Stage 4: Peak Calling
    MACS2_CALLPEAK(BLACKLIST_FILTER.out.bam, FINAL_CTRL.out.bam.first())

    // IDR (optional, narrow peaks with 2+ replicates)
    if (!params.skip_idr && params.peak_type == 'narrow') {
        ch_peaks = MACS2_CALLPEAK.out.peaks.map { it[1] }.collect()
        IDR_ANALYSIS(ch_peaks)
    }

    // Stage 5: Signal Tracks
    SIGNAL_TRACKS(MACS2_CALLPEAK.out.bdg.map { [it[0], it[1]] }, ch_chromsz.collect())

    // MultiQC
    ch_multiqc = FASTQC.out.reports
        .mix(TRIM_GALORE.out.log)
        .mix(BWA_MEM.out.flagstat)
        .mix(MARK_DUPLICATES.out.metrics)
        .mix(BLACKLIST_FILTER.out.flagstat)
        .collect()
    MULTIQC(ch_multiqc)
}
