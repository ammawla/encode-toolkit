#!/usr/bin/env nextflow
nextflow.enable.dsl=2

// ENCODE RNA-seq Pipeline — Nextflow DSL2
// FASTQ -> QC -> STAR 2-pass -> RSEM -> Kallisto (optional) -> Signal -> RSeQC

params.reads         = null
params.genome        = 'GRCh38'
params.outdir        = 'results'
params.single_end    = false
params.strandedness  = 'reverse'
params.skip_kallisto = false
params.star_index    = null
params.rsem_index    = null
params.gtf           = null
params.chrom_sizes   = null

def genome_map = [
    'GRCh38': [
        fasta:       'GRCh38.primary_assembly.genome.fa',
        gtf:         'gencode.v38.primary_assembly.annotation.gtf',
        star_index:  'GRCh38_star_index',
        rsem_index:  'GRCh38_rsem_index/GRCh38',
        kallisto_idx: 'gencode.v38.kallisto.idx',
        rseqc_bed:   'hg38_RefSeq.bed'
    ],
    'mm10': [
        fasta:       'mm10.primary_assembly.genome.fa',
        gtf:         'gencode.vM27.primary_assembly.annotation.gtf',
        star_index:  'mm10_star_index',
        rsem_index:  'mm10_rsem_index/mm10',
        kallisto_idx: 'gencode.vM27.kallisto.idx',
        rseqc_bed:   'mm10_RefSeq.bed'
    ]
]

gtf_file      = params.gtf        ?: genome_map[params.genome].gtf
star_idx_path = params.star_index  ?: genome_map[params.genome].star_index
rsem_idx_path = params.rsem_index  ?: genome_map[params.genome].rsem_index

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

process STAR_ALIGN {
    tag "$sample_id"
    publishDir "${params.outdir}/star", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)
    path(star_index)

    output:
    tuple val(sample_id), path("${sample_id}.Aligned.sortedByCoord.out.bam"),
                          path("${sample_id}.Aligned.sortedByCoord.out.bam.bai"),    emit: genome_bam
    tuple val(sample_id), path("${sample_id}.Aligned.toTranscriptome.out.bam"),      emit: transcriptome_bam
    path("${sample_id}.Log.final.out"),                                               emit: log
    path("${sample_id}.SJ.out.tab"),                                                  emit: junctions
    path("${sample_id}.ReadsPerGene.out.tab"),                                        emit: gene_counts
    tuple val(sample_id), path("${sample_id}.Signal.UniqueMultiple.str*.out.bg"),    emit: bedgraph

    script:
    def input_reads = params.single_end ? "${reads}" : "${reads[0]} ${reads[1]}"
    """
    STAR --genomeDir ${star_index} \\
      --readFilesIn ${input_reads} \\
      --readFilesCommand zcat \\
      --runThreadN ${task.cpus} \\
      --outSAMtype BAM SortedByCoordinate \\
      --outSAMunmapped Within \\
      --outFilterMultimapNmax 20 \\
      --alignSJoverhangMin 8 \\
      --alignSJDBoverhangMin 1 \\
      --outFilterMismatchNmax 999 \\
      --outFilterMismatchNoverReadLmax 0.04 \\
      --alignIntronMin 20 \\
      --alignIntronMax 1000000 \\
      --alignMatesGapMax 1000000 \\
      --quantMode TranscriptomeSAM GeneCounts \\
      --twopassMode Basic \\
      --outWigType bedGraph \\
      --outWigStrand Stranded \\
      --outFileNamePrefix ${sample_id}.

    samtools index ${sample_id}.Aligned.sortedByCoord.out.bam
    """
}

process RSEM_QUANT {
    tag "$sample_id"
    publishDir "${params.outdir}/rsem", mode: 'copy'

    input:
    tuple val(sample_id), path(transcriptome_bam)
    path(rsem_index)

    output:
    path("${sample_id}.genes.results"),    emit: genes
    path("${sample_id}.isoforms.results"), emit: isoforms
    path("${sample_id}.stat"),             emit: stats

    script:
    def pe_flag = params.single_end ? "" : "--paired-end"
    """
    rsem-calculate-expression \\
      ${pe_flag} \\
      --bam \\
      --no-bam-output \\
      --estimate-rspd \\
      --strandedness ${params.strandedness} \\
      --num-threads ${task.cpus} \\
      ${transcriptome_bam} \\
      ${rsem_index} \\
      ${sample_id}
    """
}

process KALLISTO_QUANT {
    tag "$sample_id"
    publishDir "${params.outdir}/kallisto", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)
    path(kallisto_index)

    output:
    path("${sample_id}/abundance.tsv"), emit: abundance
    path("${sample_id}/run_info.json"), emit: run_info

    when:
    !params.skip_kallisto

    script:
    def strand_flag = params.strandedness == 'reverse' ? '--rf-stranded' :
                      params.strandedness == 'forward' ? '--fr-stranded' : ''
    def input_reads = params.single_end ?
        "--single -l 200 -s 20 ${reads}" : "${reads[0]} ${reads[1]}"
    """
    kallisto quant \\
      -i ${kallisto_index} \\
      -o ${sample_id}/ \\
      ${strand_flag} \\
      -t ${task.cpus} \\
      ${input_reads}
    """
}

process SIGNAL_TRACKS {
    tag "$sample_id"
    publishDir "${params.outdir}/signal", mode: 'copy'

    input:
    tuple val(sample_id), path(bedgraphs)
    path(chrom_sizes)

    output:
    path("${sample_id}_plus.bw"),  emit: plus_bw
    path("${sample_id}_minus.bw"), emit: minus_bw

    script:
    """
    # Sort and convert plus strand bedGraph to bigWig
    sort -k1,1 -k2,2n ${sample_id}.Signal.UniqueMultiple.str1.out.bg > plus_sorted.bg
    bedGraphToBigWig plus_sorted.bg ${chrom_sizes} ${sample_id}_plus.bw

    # Sort and convert minus strand bedGraph to bigWig
    sort -k1,1 -k2,2n ${sample_id}.Signal.UniqueMultiple.str2.out.bg > minus_sorted.bg
    bedGraphToBigWig minus_sorted.bg ${chrom_sizes} ${sample_id}_minus.bw
    """
}

process RSEQC {
    tag "$sample_id"
    publishDir "${params.outdir}/qc/rseqc", mode: 'copy'

    input:
    tuple val(sample_id), path(bam), path(bai)
    path(rseqc_bed)

    output:
    path("${sample_id}.infer_experiment.txt"),     emit: strandedness
    path("${sample_id}.read_distribution.txt"),    emit: read_dist
    path("${sample_id}.geneBody_coverage*"),        emit: gene_body
    path("${sample_id}.inner_distance*"),           emit: inner_dist, optional: true

    script:
    def inner_dist_cmd = params.single_end ? "" :
        "inner_distance.py -r ${rseqc_bed} -i ${bam} -o ${sample_id}.inner_distance"
    """
    infer_experiment.py -r ${rseqc_bed} -i ${bam} > ${sample_id}.infer_experiment.txt
    read_distribution.py -r ${rseqc_bed} -i ${bam} > ${sample_id}.read_distribution.txt
    geneBody_coverage.py -r ${rseqc_bed} -i ${bam} -o ${sample_id}.geneBody_coverage
    ${inner_dist_cmd}
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
    ch_reads      = Channel.fromFilePairs(params.reads, size: params.single_end ? 1 : 2)
    ch_star_idx   = Channel.fromPath(star_idx_path, type: 'dir')
    ch_rsem_idx   = Channel.fromPath(rsem_idx_path, type: 'dir')
    ch_rseqc_bed  = Channel.fromPath(genome_map[params.genome].rseqc_bed)

    // Stage 1: QC and Trimming
    FASTQC(ch_reads)
    TRIM_GALORE(ch_reads)

    // Stage 2: STAR Alignment (2-pass mode)
    STAR_ALIGN(TRIM_GALORE.out.trimmed, ch_star_idx.collect())

    // Stage 3: Quantification
    RSEM_QUANT(STAR_ALIGN.out.transcriptome_bam, ch_rsem_idx.collect())

    // Kallisto (optional)
    if (!params.skip_kallisto) {
        ch_kallisto_idx = Channel.fromPath(genome_map[params.genome].kallisto_idx)
        KALLISTO_QUANT(TRIM_GALORE.out.trimmed, ch_kallisto_idx.collect())
    }

    // Stage 4: Signal Tracks
    ch_chrom_sizes = params.chrom_sizes ?
        Channel.fromPath(params.chrom_sizes) :
        Channel.fromPath("${star_idx_path}/chrNameLength.txt")
    SIGNAL_TRACKS(STAR_ALIGN.out.bedgraph, ch_chrom_sizes.collect())

    // Stage 5: QC Metrics
    RSEQC(STAR_ALIGN.out.genome_bam, ch_rseqc_bed.collect())

    // MultiQC aggregation
    ch_multiqc = FASTQC.out.reports
        .mix(TRIM_GALORE.out.log)
        .mix(STAR_ALIGN.out.log)
        .mix(RSEM_QUANT.out.stats)
        .mix(RSEQC.out.strandedness)
        .mix(RSEQC.out.read_dist)
        .collect()
    MULTIQC(ch_multiqc)
}
