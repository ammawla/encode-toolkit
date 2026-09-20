#!/usr/bin/env python3
"""Keep the skill documentation honest about the code it describes.

1. Every ``encode_*`` tool call shown in a skill must name a real MCP tool and use only
   keyword arguments that the tool accepts (read from the server source with ``ast``).
2. Every ``nextflow run`` example in a pipeline skill must use only parameters that the
   pipeline declares and only profiles that its nextflow.config defines.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
SERVER = ROOT / "src" / "encode_connector" / "server" / "main.py"

CALL_RE = re.compile(r"\b(encode_[a-z_]+)\s*\(")
KEYWORD_RE = re.compile(r"\s*([A-Za-z_]\w*)\s*=(?!=)")
FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
FLAG_RE = re.compile(r"(?<![\w-])--([A-Za-z_]\w*)")
PROFILE_RE = re.compile(r"(?<![\w-])-profile[ =]+([\w,]+)")


def tool_signatures() -> dict[str, set[str]]:
    tree = ast.parse(SERVER.read_text())
    return {
        node.name: {arg.arg for arg in node.args.args + node.args.kwonlyargs}
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef) and node.name.startswith("encode_")
    }


def call_arguments(text: str, start: int) -> str | None:
    """Return the text between the parentheses that open at ``start - 1``, without # comments."""
    depth, quote, comment, arguments = 1, None, False, ""
    for index in range(start, len(text)):
        char = text[index]
        if comment:
            comment = char != "\n"
            if comment:
                continue
        elif quote:
            quote = None if char == quote else quote
        elif char == "#":  # an inline comment may hold an apostrophe: "# user's tissue"
            comment = True
            continue
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return arguments
        arguments += char
    return None


def top_level_arguments(arguments: str) -> list[str]:
    parts, current, depth, quote = [], "", 0, None
    for char in arguments:
        if quote:
            quote = None if char == quote else quote
        elif char in "\"'":
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0 and not quote:
            parts.append(current)
            current = ""
        else:
            current += char
    return [*parts, current]


def check_tool_calls(signatures: dict[str, set[str]]) -> list[str]:
    problems = []
    for doc in sorted(SKILLS.rglob("*.md")):
        text = doc.read_text()
        for match in CALL_RE.finditer(text):
            tool = match.group(1)
            arguments = call_arguments(text, match.end())
            where = f"{doc.relative_to(ROOT)}:{text.count(chr(10), 0, match.start()) + 1}"
            if arguments is None:
                problems.append(f"{where}: could not find the end of this {tool}(...) call")
                continue
            if tool not in signatures:
                problems.append(f"{where}: unknown tool {tool}")
                continue
            for argument in top_level_arguments(arguments):
                keyword = KEYWORD_RE.match(argument)
                if keyword and keyword.group(1) not in signatures[tool]:
                    accepted = ", ".join(sorted(signatures[tool]))
                    problems.append(f"{where}: {tool}() has no parameter '{keyword.group(1)}' (accepts: {accepted})")
    return problems


def pipeline_contract(scripts: Path) -> tuple[set[str], set[str]]:
    """Parameters and profiles declared by one pipeline's main.nf and nextflow.config."""
    workflow = (scripts / "main.nf").read_text()
    config = (scripts / "nextflow.config").read_text()
    params = set(re.findall(r"^params\.(\w+)\s*=", workflow, re.M))
    params_block = re.search(r"^params\s*\{(.*?)^\}", config, re.S | re.M)
    if params_block:
        params |= set(re.findall(r"^\s*(\w+)\s*=", params_block.group(1), re.M))
    profiles_block = re.search(r"^profiles\s*\{(.*?)^\}", config, re.S | re.M)
    profiles = set(re.findall(r"^    (\w+)\s*\{", profiles_block.group(1), re.M)) if profiles_block else set()
    return params, profiles


def nextflow_commands(text: str):
    """Yield (line number, command) for each ``nextflow run`` command inside a fenced block."""
    for block in FENCE_RE.finditer(text):
        first_line = text.count("\n", 0, block.start(1)) + 1
        lines = block.group(1).split("\n")
        index = 0
        while index < len(lines):
            if re.search(r"\bnextflow\s+run\b", lines[index]):
                start, command = index, lines[index]
                while command.rstrip().endswith("\\") and index + 1 < len(lines):
                    index += 1
                    command = command.rstrip()[:-1] + " " + lines[index]
                yield first_line + start, command
            index += 1


def check_pipeline_examples() -> list[str]:
    contracts = {
        scripts.parent.name: pipeline_contract(scripts)
        for scripts in sorted(SKILLS.glob("pipeline-*/scripts"))
        if (scripts / "main.nf").exists()
    }
    all_params = set().union(*(params for params, _ in contracts.values()))
    all_profiles = set().union(*(profiles for _, profiles in contracts.values()))
    problems = []
    for doc in sorted(SKILLS.rglob("*.md")):
        skill = doc.relative_to(SKILLS).parts[0]
        text = doc.read_text()
        for line, command in nextflow_commands(text):
            named = re.search(r"(pipeline-\w+)", command)
            if skill in contracts:
                params, profiles = contracts[skill]
            elif named and named.group(1) in contracts:
                params, profiles = contracts[named.group(1)]
            elif skill.startswith("pipeline-"):
                params, profiles = all_params, all_profiles
            else:
                continue  # a third-party workflow, not one of the pipeline skills
            where = f"{doc.relative_to(ROOT)}:{line}"
            for flag in FLAG_RE.findall(command):
                if flag not in params:
                    problems.append(f"{where}: --{flag} is not a parameter of this pipeline")
            for selection in PROFILE_RE.findall(command):
                for profile in selection.split(","):
                    if profile not in profiles:
                        problems.append(
                            f"{where}: -profile {profile} is not defined (profiles: {', '.join(sorted(profiles))})"
                        )
    return problems


def main() -> int:
    problems = check_tool_calls(tool_signatures()) + check_pipeline_examples()
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
