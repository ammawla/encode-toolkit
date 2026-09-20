#!/usr/bin/env python3
"""Generate the nextflow.config of every pipeline skill from one template.

The seven configs differ only in their title, resource ceilings and per-process resources.
Edit this file, run it from anywhere, and commit the regenerated configs together with the
identical copies under plugin/skills/. CI reruns it and fails if any config differs.
"""

from __future__ import annotations

from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills"

# default: (cpus, memory, time) for processes that do not set their own resources in main.nf
# procs:   (process name, cpus, memory, time); memory and time scale with task.attempt
PIPES = {
    "chipseq": dict(
        title="ChIP-seq",
        cpus=16,
        mem="64.GB",
        time="24.h",
        default=("4", "16.GB", "4.h"),
        procs=[
            ("BWA_MEM", "8", "32.GB", "8.h"),
            ("MARK_DUPLICATES", "4", "16.GB", "4.h"),
            ("MACS2_CALLPEAK", "2", "8.GB", "2.h"),
            ("SIGNAL_TRACKS", "2", "8.GB", "2.h"),
            ("MULTIQC", "1", "4.GB", "1.h"),
        ],
    ),
    "atacseq": dict(
        title="ATAC-seq",
        cpus=16,
        mem="64.GB",
        time="24.h",
        default=("4", "16.GB", "4.h"),
        procs=[
            ("BOWTIE2_ALIGN", "8", "32.GB", "8.h"),
            ("MARK_DUPLICATES", "4", "16.GB", "4.h"),
            ("TN5_SHIFT", "4", "16.GB", "2.h"),
            ("NFR_SELECTION", "4", "8.GB", "2.h"),
            ("MACS2_CALLPEAK", "2", "8.GB", "2.h"),
            ("SIGNAL_TRACKS", "4", "8.GB", "2.h"),
            ("MULTIQC", "1", "4.GB", "1.h"),
        ],
    ),
    "rnaseq": dict(
        title="RNA-seq",
        cpus=16,
        mem="64.GB",
        time="24.h",
        default=("4", "16.GB", "4.h"),
        procs=[
            ("STAR_ALIGN", "8", "36.GB", "8.h"),
            ("RSEM_QUANT", "8", "16.GB", "4.h"),
            ("KALLISTO_QUANT", "4", "8.GB", "1.h"),
            ("SIGNAL_TRACKS", "2", "8.GB", "2.h"),
            ("RSEQC", "2", "8.GB", "2.h"),
            ("MULTIQC", "1", "4.GB", "1.h"),
        ],
    ),
    "cutandrun": dict(
        title="CUT&RUN",
        cpus=16,
        mem="16.GB",
        time="12.h",
        default=None,
        procs=[
            ("BOWTIE2_ALIGN", "8", "8.GB", "2.h"),
            ("FILTER_DEDUP", "4", "8.GB", "1.h"),
            ("SEACR_PEAKS", "2", "4.GB", "1.h"),
            ("SIGNAL_TRACK", "4", "8.GB", "1.h"),
        ],
    ),
    "dnaseseq": dict(
        title="DNase-seq",
        cpus=16,
        mem="32.GB",
        time="24.h",
        default=None,
        procs=[
            ("BWA_ALIGN", "8", "16.GB", "4.h"),
            ("FILTER_DEDUP", "4", "8.GB", "2.h"),
            ("HOTSPOT2", "4", "8.GB", "2.h"),
            ("FOOTPRINTING", "4", "8.GB", "4.h"),
        ],
    ),
    "hic": dict(
        title="Hi-C",
        cpus=16,
        mem="128.GB",
        time="48.h",
        default=None,
        procs=[
            ("BWA_ALIGN", "8", "16.GB", "8.h"),
            ("JUICER_HIC", "4", "64.GB", "6.h"),
            ("HICCUPS", "4", "16.GB", "4.h"),
        ],
    ),
    "wgbs": dict(
        title="WGBS",
        cpus=16,
        mem="64.GB",
        time="48.h",
        default=None,
        procs=[
            ("BISMARK_ALIGN", "8", "48.GB", "24.h"),
            ("DEDUPLICATE", "2", "16.GB", "4.h"),
            ("METHYLDACKEL_EXTRACT", "4", "8.GB", "4.h"),
        ],
    ),
}

TEMPLATE = """// ============================================================================
// ENCODE {title} Pipeline — Nextflow Configuration
// Profiles: local, slurm, gcp, aws
// ============================================================================

params {{
    outdir     = './results'

    // Upper bounds applied to every process through process.resourceLimits
    max_cpus   = {cpus}
    max_memory = '{mem}'
    max_time   = '{time}'

    // Container image. It is built from the Dockerfile that ships with this skill:
    //   docker build -t {image} scripts/
    // For the slurm profile, convert it once and pass the image file:
    //   singularity build {name}.sif docker-daemon://{image}
    //   nextflow run main.nf -profile slurm --container /path/to/{name}.sif ...
    // For the gcp and aws profiles, push the image to a registry you control and
    // pass its full name with --container.
    container  = '{image}'

    // Scheduler and cloud settings (only read by the matching profile).
    // Google Batch and AWS Batch stage every task through object storage, so the gcp
    // profile needs --gcp_project and --gcp_workdir gs://<bucket>/work, and the aws profile
    // needs --aws_queue and --aws_workdir s3://<bucket>/work. main.nf stops with a clear
    // message when one is missing. --outdir only sets where results are published.
    slurm_queue   = 'normal'
    slurm_account = null
    gcp_project   = null
    gcp_location  = 'us-central1'
    gcp_workdir   = null
    gcp_disk      = '200.GB'
    aws_queue     = null
    aws_region    = 'us-east-1'
    aws_workdir   = null
    // The pipeline image does not contain the AWS CLI, so AWS Batch tasks use the one on the
    // compute environment's AMI. The default is the custom-AMI layout from Nextflow's AWS Batch
    // guide; pass --aws_cli_path when your AMI keeps it somewhere else.
    aws_cli_path  = '/home/ec2-user/miniconda/bin/aws'
}}

process {{
    container      = params.container
    // Retry with more memory and time only when a task was killed for exceeding them
    // (exit codes 130-145 and 104). Any other failure is a real error: stop and report it.
    errorStrategy  = {{ task.exitStatus in ((130..145) + 104) ? 'retry' : 'finish' }}
    maxRetries     = 2
    resourceLimits = [cpus: params.max_cpus, memory: params.max_memory, time: params.max_time]
{default}
{procs}}}

profiles {{
    local {{
        process.executor  = 'local'
        docker.enabled    = true
        docker.runOptions = '-u $(id -u):$(id -g)'
    }}

    slurm {{
        process.executor       = 'slurm'
        process.queue          = params.slurm_queue
        process.clusterOptions = params.slurm_account ? "--account=${{params.slurm_account}}" : null
        singularity.enabled    = true
        singularity.autoMounts = true
    }}

    gcp {{
        process.executor  = 'google-batch'
        process.disk      = params.gcp_disk
        google.project    = params.gcp_project
        google.location   = params.gcp_location
        google.batch.spot = true
        google.batch.maxSpotAttempts = 3   // rerun a task whose spot VM was reclaimed
        workDir           = params.gcp_workdir
    }}

    aws {{
        process.executor  = 'awsbatch'
        process.queue     = params.aws_queue
        aws.region        = params.aws_region
        aws.batch.cliPath = params.aws_cli_path
        workDir           = params.aws_workdir
    }}
}}

timeline {{
    enabled   = true
    overwrite = true
    file      = "${{params.outdir}}/pipeline_info/timeline.html"
}}

report {{
    enabled   = true
    overwrite = true
    file      = "${{params.outdir}}/pipeline_info/report.html"
}}

trace {{
    enabled   = true
    overwrite = true
    file      = "${{params.outdir}}/pipeline_info/trace.txt"
}}
"""


def render(name: str, cfg: dict) -> str:
    default = ""
    if cfg["default"]:
        cpus, memory, time = cfg["default"]
        default = (
            "\n    // Default for every process that is not listed below\n"
            f"    cpus   = {cpus}\n    memory = {{ {memory} * task.attempt }}\n    time   = {{ {time} * task.attempt }}\n"
        )
    procs = "".join(
        f"    withName: '{proc}' {{\n        cpus   = {cpus}\n"
        f"        memory = {{ {memory} * task.attempt }}\n        time   = {{ {time} * task.attempt }}\n    }}\n"
        for proc, cpus, memory, time in cfg["procs"]
    )
    return TEMPLATE.format(
        title=cfg["title"],
        cpus=cfg["cpus"],
        mem=cfg["mem"],
        time=cfg["time"],
        image=f"encode-toolkit/pipeline-{name}:1.0.0",
        name=f"pipeline-{name}",
        procs=procs,
        default=default,
    )


def main() -> None:
    for name, cfg in PIPES.items():
        (SKILLS / f"pipeline-{name}" / "scripts" / "nextflow.config").write_text(render(name, cfg))


if __name__ == "__main__":
    main()
