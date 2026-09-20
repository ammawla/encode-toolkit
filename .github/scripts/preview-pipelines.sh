#!/usr/bin/env bash
# Validate every pipeline skill without reference data:
#   1. `nextflow lint` on main.nf and nextflow.config (strict syntax)
#   2. `nextflow run -preview`, which builds the workflow graph from placeholder inputs and
#      so checks parameter validation and channel/process wiring, but runs no tasks
#   3. every profile of every config must resolve
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../skills" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
export NXF_ANSI_LOG=false

mkdir -p "$WORK/fq" "$WORK/ctl" "$WORK/ref/rsem" "$WORK/ref/star_index" "$WORK/ref/bismark_genome" \
         "$WORK/GRCh38_index" "$WORK/GRCh38_bowtie2_index" "$WORK/ref/rgtdata"
for sample in sampleA sampleB; do
    : > "$WORK/fq/${sample}_R1.fastq.gz"; : > "$WORK/fq/${sample}_R2.fastq.gz"
done
: > "$WORK/ctl/input1_R1.fastq.gz"; : > "$WORK/ctl/input1_R2.fastq.gz"
for f in genome.fa genome.fa.bwt genome.1.bt2 spike.1.bt2 chrom.sizes blacklist.bed center_sites.starch \
         mappable.bed control.bam rsem/GRCh38.grp rsem/GRCh38.seq star_index/chrNameLength.txt \
         bismark_genome/genome.fa; do
    : > "$WORK/ref/$f"
done
: > "$WORK/gencode.v38.kallisto.idx"; : > "$WORK/hg38_RefSeq.bed"
: > "$WORK/ref/kallisto.idx"; : > "$WORK/ref/genes.bed"

READS="$WORK/fq/*_R{1,2}.fastq.gz"
REF="$WORK/ref"
failures=0

preview() {   # preview <pipeline> <label> <expected: pass|fail|error text> [nextflow args...]
    # Any expectation other than pass or fail is text the run must fail with.
    local pipeline=$1 label=$2 expected=$3 message=""; shift 3
    local scripts="$SKILLS_DIR/pipeline-$pipeline/scripts" status=pass
    if [ "$expected" != pass ] && [ "$expected" != fail ]; then message=$expected; expected=fail; fi
    (cd "$WORK" && nextflow -q run "$scripts/main.nf" -c "$scripts/nextflow.config" -preview \
        --outdir "$WORK/out" "$@" > "$WORK/log.txt" 2>&1) || status=fail
    if [ -n "$message" ] && ! grep -qF -- "$message" "$WORK/log.txt"; then status="fail without '$message'"; fi
    if [ "$status" = "$expected" ]; then
        echo "  ok    $pipeline: $label"
    else
        echo "  FAIL  $pipeline: $label (expected $expected, got $status)"; sed 's/^/        /' "$WORK/log.txt" | tail -8
        failures=$((failures + 1))
    fi
}

echo "== nextflow lint =="
for dir in "$SKILLS_DIR"/pipeline-*/scripts; do
    [ -f "$dir/main.nf" ] || continue
    if nextflow lint "$dir/main.nf" "$dir/nextflow.config" > "$WORK/lint.txt" 2>&1; then
        echo "  ok    $(basename "$(dirname "$dir")")"
    else
        echo "  FAIL  $(basename "$(dirname "$dir")")"; grep -E "^Error" "$WORK/lint.txt" | head -10 | sed 's/^/        /'
        failures=$((failures + 1))
    fi
done

echo "== nextflow run -preview =="
preview atacseq "defaults" pass --reads "$READS" --blacklist "$REF/blacklist.bed"
preview atacseq "unsupported genome is rejected" fail --reads "$READS" --genome hg19
preview atacseq "single-end input is rejected" fail --reads "$READS" --blacklist "$REF/blacklist.bed" --single_end
preview atacseq "explicit --bowtie2_index" pass --reads "$READS" --blacklist "$REF/blacklist.bed" \
    --bowtie2_index "$WORK/GRCh38_bowtie2_index"
preview chipseq "samples with control" pass --reads "$READS" --control "$WORK/ctl/*_R{1,2}.fastq.gz" \
    --chrom_sizes "$REF/chrom.sizes" --blacklist "$REF/blacklist.bed"
preview chipseq "no control, broad peaks, explicit --bwa_index" pass --reads "$READS" --peak_type broad \
    --chrom_sizes "$REF/chrom.sizes" --blacklist "$REF/blacklist.bed" --bwa_index "$WORK/GRCh38_index"
preview chipseq "missing --chrom_sizes is rejected" "Missing required parameter: --chrom_sizes" --reads "$READS" \
    --blacklist "$REF/blacklist.bed"
CUTANDRUN=(--reads "$READS" --bowtie2_index "$REF/genome" --chrom_sizes "$REF/chrom.sizes" --blacklist "$REF/blacklist.bed")
preview cutandrun "minimal" pass "${CUTANDRUN[@]}"
preview cutandrun "control + spike-in + both callers" pass "${CUTANDRUN[@]}" --spikein_index "$REF/spike" \
    --control "$REF/control.bam" --peak_caller both --seacr_mode both
preview cutandrun "invalid --seacr_mode is rejected" fail "${CUTANDRUN[@]}" --seacr_mode bogus
DNASE=(--reads "$READS" --bwa_index "$REF/genome.fa" --chrom_sizes "$REF/chrom.sizes" --blacklist "$REF/blacklist.bed")
preview dnaseseq "center sites + mappable + footprinting" pass "${DNASE[@]}" --hotspot_center_sites "$REF/center_sites.starch" \
    --hotspot_mappable "$REF/mappable.bed" --rgt_data "$REF/rgtdata"
preview dnaseseq "skip footprinting needs no RGT data" pass "${DNASE[@]}" --hotspot_center_sites "$REF/center_sites.starch" \
    --skip_footprint
preview dnaseseq "footprinting without --rgt_data is rejected" fail "${DNASE[@]}" --hotspot_center_sites "$REF/center_sites.starch"
preview dnaseseq "missing center sites is rejected" fail "${DNASE[@]}" --skip_footprint
preview hic "defaults" pass --reads "$READS" --bwa_index "$REF/genome.fa" --chrom_sizes "$REF/chrom.sizes"
RNASEQ=(--reads "$READS" --star_index "$REF/star_index" --rsem_index "$REF/rsem/GRCh38")
preview rnaseq "RSEM reference given as a prefix" pass "${RNASEQ[@]}"
preview rnaseq "explicit kallisto index and RSeQC gene model, unstranded" pass "${RNASEQ[@]}" --strandedness none \
    --kallisto_index "$REF/kallisto.idx" --rseqc_bed "$REF/genes.bed"
preview rnaseq "invalid --strandedness is rejected" "Invalid --strandedness" "${RNASEQ[@]}" --strandedness auto
preview wgbs "defaults" pass --reads "$READS" --genome_dir "$REF/bismark_genome"
preview wgbs "skip dedup, per-cytosine output" pass --reads "$READS" --genome_dir "$REF/bismark_genome" \
    --skip_dedup --merge_context false

echo "== cloud profiles need a bucket work directory and a project or queue =="
for pipeline in atacseq chipseq cutandrun dnaseseq hic rnaseq wgbs; do
    case $pipeline in
        atacseq)   ARGS=(--reads "$READS" --blacklist "$REF/blacklist.bed") ;;
        chipseq)   ARGS=(--reads "$READS" --chrom_sizes "$REF/chrom.sizes" --blacklist "$REF/blacklist.bed") ;;
        cutandrun) ARGS=("${CUTANDRUN[@]}") ;;
        dnaseseq)  ARGS=("${DNASE[@]}" --hotspot_center_sites "$REF/center_sites.starch" --skip_footprint) ;;
        hic)       ARGS=(--reads "$READS" --bwa_index "$REF/genome.fa" --chrom_sizes "$REF/chrom.sizes") ;;
        rnaseq)    ARGS=("${RNASEQ[@]}") ;;
        wgbs)      ARGS=(--reads "$READS" --genome_dir "$REF/bismark_genome") ;;
    esac
    preview "$pipeline" "-profile gcp without project and work directory" "requires --gcp_project" -profile gcp "${ARGS[@]}"
    preview "$pipeline" "-profile aws without queue and work directory" "requires --aws_queue" -profile aws "${ARGS[@]}"
done

echo "== config profiles =="
for dir in "$SKILLS_DIR"/pipeline-*/scripts; do
    [ -f "$dir/nextflow.config" ] || continue
    for profile in local slurm gcp aws; do
        if (cd "$WORK" && nextflow -q config -profile "$profile" "$dir" > "$WORK/cfg.txt" 2>&1) \
            && ! grep -q "^ERROR" "$WORK/cfg.txt"; then
            :
        else
            echo "  FAIL  $(basename "$(dirname "$dir")") -profile $profile"; head -4 "$WORK/cfg.txt" | sed 's/^/        /'
            failures=$((failures + 1))
        fi
    done
done
echo "  checked every profile of every pipeline"

if [ "$failures" -gt 0 ]; then echo "$failures check(s) failed"; exit 1; fi
echo "All pipeline checks passed"
