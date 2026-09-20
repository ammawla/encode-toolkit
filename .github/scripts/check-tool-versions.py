#!/usr/bin/env python3
"""Every pipeline image must use the tool versions its conda environment pins.

For each pipeline, read the pinned packages from
``skills/bioinformatics-installer/environments/<pipeline>-env.yml`` and look for the same tool
in ``skills/pipeline-<pipeline>/scripts/Dockerfile``. When the Dockerfile names a version of
that tool, it has to be the one conda pins. Tools that only one side ships are ignored.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills"
ENVIRONMENTS = SKILLS / "bioinformatics-installer" / "environments"

# conda package name -> how the tool is spelled in a Dockerfile (download URLs, pip pins)
DOCKERFILE_NAMES = {
    "trim-galore": r"trim[-_ ]?galore",
    "rseqc": r"rseqc",
    "star": r"star",
    "bismark": r"bismark",
    "methyldackel": r"methyldackel",
}
CONDA_PIN = re.compile(r"^\s*-\s*([A-Za-z][\w.-]*?)\s*==?\s*(\d[\w.]*)\s*$", re.M)
PIP_PIN = re.compile(r"^\s*-\s*([A-Za-z][\w.-]*?)==(\d[\w.]*)\s*$", re.M)
VERSION = r"(\d+\.\d+(?:\.\d+)*[a-z]?)"


def dockerfile_versions(dockerfile: str, tool: str) -> set[str]:
    """Versions that follow the tool's name: samtools-1.19, multiqc==1.21, picard/releases/download/3.1.1."""
    name = DOCKERFILE_NAMES.get(tool, re.escape(tool))
    between = r"(?:[-_=/ v]|linux|releases/download|archive|refs/tags)*"
    return set(re.findall(rf"(?i)(?<![\w]){name}{between}{VERSION}", dockerfile))


def main() -> int:
    problems = []
    for environment in sorted(ENVIRONMENTS.glob("*-env.yml")):
        pipeline = environment.name.removesuffix("-env.yml")
        dockerfile_path = SKILLS / f"pipeline-{pipeline}" / "scripts" / "Dockerfile"
        if not dockerfile_path.exists():
            continue
        text = environment.read_text()
        dockerfile = dockerfile_path.read_text()
        pins = dict(CONDA_PIN.findall(text)) | dict(PIP_PIN.findall(text))
        for tool, conda_version in sorted(pins.items()):
            if tool == "python":
                continue
            image_versions = dockerfile_versions(dockerfile, tool)
            if image_versions and conda_version not in image_versions:
                problems.append(
                    f"pipeline-{pipeline}: {tool} is {', '.join(sorted(image_versions))} in the Dockerfile "
                    f"but {conda_version} in {environment.name}"
                )
    for problem in problems:
        print(problem)
    print(f"{len(problems)} version mismatch(es)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
