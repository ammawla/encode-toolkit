#!/usr/bin/env python3
"""Every pipeline image must use the tool versions its conda environment pins.

For each pipeline, compare ``skills/bioinformatics-installer/environments/<pipeline>-env.yml``
with ``skills/pipeline-<pipeline>/scripts/Dockerfile``:

1. A tool the environment pins exactly must have that version in the Dockerfile, whenever the
   Dockerfile names a version of it (Java included: ``openjdk=17`` and ``openjdk-17-jre-headless``).
2. A tool the Dockerfile pins must be pinned exactly in the environment too: pip pins
   (``cutadapt==4.6``), and source or binary downloads (``samtools-1.19.tar.bz2``) of any tool
   that some environment pins.
3. A tool that both sides install but the environment does not pin exactly must be listed in
   ``NOT_COMPARED`` with the reason. Those are printed on every run, so nothing is skipped silently.

Tools that only one side ships are ignored.
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
    "ucsc-bedgraphtobigwig": r"bedGraphToBigWig",
}
# tools whose version is a single number on both sides: "openjdk=17" and "openjdk-17-jre-headless"
MAJOR_ONLY = {"openjdk"}
# apt packages that install whatever version the base image happens to carry
UNVERSIONED_IN_IMAGE = {"openjdk": r"default-j(?:re|dk)"}
UBUNTU = "comes from the ubuntu:22.04 archive in the image, which fixes its version"
NOT_COMPARED = {
    "numpy": "build constraint for MACS2's extension in the image; conda's MACS2 build brings its own",
    "r-base": f"interpreter; {UBUNTU} (SEACR needs base R only)",
    "bedops": UBUNTU,
    "ucsc-bedgraphtobigwig": "UCSC publishes its binaries at an unversioned URL, so neither side can pin it",
    "pigz": UBUNTU,
    "wget": UBUNTU,
    "curl": UBUNTU,
}
# "- samtools==1.19", "- bioconda::samtools==1.19", "- samtools=1.19=h50ea8bc_0  # note", "- r-base>=4.3", "- pigz"
DEPENDENCY = re.compile(r"^\s*-\s*(?:[\w-]+::)?([A-Za-z][\w.-]*)\s*([<>=!~][^\s#]*)?\s*(?:#.*)?$", re.M)
# conda reads "samtools=1.19" as a prefix (it resolved to 1.19.2); only "==1.19" or a spec with
# a build string ("=1.19=h50ea8bc_0") fixes the version
EXACT = re.compile(r"==(\d[\w.]*)|=(\d[\w.]*)=[\w.]+")
FUZZY = re.compile(r"=(\d[\w.]*)")
PIP_IN_IMAGE = re.compile(r"(?<![\w.-])([A-Za-z][\w.-]*)==(\d[\w.]*)")
VERSION = r"(\d+\.\d+(?:\.\d+)*[a-z]?)"


def instructions(dockerfile: str) -> str:
    """The Dockerfile without comments: "# samtools 1.19" says nothing about what is installed."""
    return "\n".join(line for line in dockerfile.splitlines() if not line.lstrip().startswith("#"))


def dockerfile_versions(dockerfile: str, tool: str) -> set[str]:
    """Versions that follow the tool's name: samtools-1.19, multiqc==1.21, picard/releases/download/3.1.1."""
    name = DOCKERFILE_NAMES.get(tool, re.escape(tool))
    between = r"(?:[-_=/ v]|linux|releases/download|archive|refs/tags)*"
    version = r"(\d+)(?![\w.])" if tool in MAJOR_ONLY else VERSION
    return set(re.findall(rf"(?i)(?<![\w]){name}{between}{version}", instructions(dockerfile)))


def environment_pins(text: str) -> dict[str, str | None]:
    """Package -> exact version, or None when the environment lists it without an exact pin.

    Tools compared by release line (Java) are exact with "openjdk=17".
    """
    pins = {}
    for name, spec in DEPENDENCY.findall(text):
        exact = EXACT.fullmatch(spec)
        if exact:
            pins[name.lower()] = exact.group(1) or exact.group(2)
        elif name.lower() in MAJOR_ONLY and FUZZY.fullmatch(spec):
            pins[name.lower()] = FUZZY.fullmatch(spec).group(1)
        else:
            pins[name.lower()] = None
    return pins


def compare(pipeline: str, environment: str, dockerfile: str, tracked: set[str]) -> tuple[list[str], list[str], int]:
    """Problems, tools deliberately not compared, and the number of versions compared.

    ``tracked`` holds every tool that some environment pins: when this image names a version of
    one, this environment has to pin it as well.
    """
    problems, skipped, compared = [], [], 0
    pins = environment_pins(environment)
    image = instructions(dockerfile)
    for tool, conda_version in sorted(pins.items()):
        if tool in ("python", "pip"):
            continue
        image_versions = dockerfile_versions(dockerfile, tool)
        name = DOCKERFILE_NAMES.get(tool, re.escape(tool))
        named_in_image = image_versions or re.search(rf"(?i)(?<![\w-]){name}(?![\w-])", image)
        unversioned = (
            re.search(rf"(?<![\w-]){UNVERSIONED_IN_IMAGE[tool]}(?![\w-])", image)
            if tool in UNVERSIONED_IN_IMAGE
            else None
        )
        if unversioned:
            problems.append(
                f"pipeline-{pipeline}: the image installs {unversioned.group(0)}, which does not fix the {tool} version"
            )
            continue
        if conda_version is None:
            if not named_in_image:
                continue
            if tool in NOT_COMPARED:
                skipped.append(f"pipeline-{pipeline}: {tool} is not compared: {NOT_COMPARED[tool]}")
            else:
                problems.append(
                    f"pipeline-{pipeline}: {tool} is in the image but has no exact pin in the environment "
                    '(write "==version"; a single "=" is a prefix match in conda)'
                )
        elif image_versions:
            compared += 1
            if conda_version not in image_versions:
                problems.append(
                    f"pipeline-{pipeline}: {tool} is {', '.join(sorted(image_versions))} in the Dockerfile "
                    f"but {conda_version} in the environment"
                )
    for tool in sorted(tracked - set(pins)):
        image_versions = dockerfile_versions(dockerfile, tool)
        if image_versions and tool not in NOT_COMPARED:
            problems.append(
                f"pipeline-{pipeline}: the image installs {tool} {', '.join(sorted(image_versions))} "
                "but the environment does not list it"
            )
    for package, version in sorted(set(PIP_IN_IMAGE.findall(image))):
        if pins.get(package.lower()) is not None:
            continue  # compared above
        if package.lower() in NOT_COMPARED:
            skipped.append(f"pipeline-{pipeline}: {package} is not compared: {NOT_COMPARED[package.lower()]}")
        else:
            problems.append(f"pipeline-{pipeline}: the image pins {package}=={version} but the environment does not")
    return problems, skipped, compared


def main() -> int:
    problems, skipped, compared = [], [], 0
    environments = sorted(ENVIRONMENTS.glob("*-env.yml"))
    tracked = {
        tool
        for environment in environments
        for tool, version in environment_pins(environment.read_text()).items()
        if version is not None and tool not in ("python", "pip")
    }
    for environment in environments:
        pipeline = environment.name.removesuffix("-env.yml")
        dockerfile = SKILLS / f"pipeline-{pipeline}" / "scripts" / "Dockerfile"
        if dockerfile.exists():
            found, not_compared, count = compare(pipeline, environment.read_text(), dockerfile.read_text(), tracked)
            problems += found
            skipped += not_compared
            compared += count
    for line in skipped + problems:
        print(line)
    print(f"{compared} versions compared, {len(skipped)} not compared, {len(problems)} version mismatch(es)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
