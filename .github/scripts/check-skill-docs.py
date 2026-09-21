#!/usr/bin/env python3
"""Keep the skill documentation honest about the code it describes.

1. Every ``encode_*`` tool call shown in a skill must name a real MCP tool, pass every required
   argument, and use only keyword arguments and values that the tool accepts: ``Literal``
   choices, and for filters such as ``assay_title`` the server's catalog of ENCODE values
   (all read from the source with ``ast``).
2. Every ``nextflow run`` example in a pipeline skill must use only parameters that the
   pipeline declares and only profiles that its nextflow.config defines.
3. A JSON example that directly follows a tool call is that tool's output, so every field name
   in it must be one the server can emit (a field of its models or a key it writes).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
SERVER = ROOT / "src" / "encode_connector" / "server" / "main.py"
CONSTANTS = ROOT / "src" / "encode_connector" / "client" / "constants.py"
# tool parameter -> the list in constants.py that holds the values ENCODE uses for it
CATALOGS = {
    "assay_title": "ASSAY_TITLES",
    "organism": "ORGANISMS",
    "organ": "ORGAN_SLIMS",
    "biosample_type": "BIOSAMPLE_CLASSIFICATIONS",
    "file_format": "FILE_FORMATS",
    "output_type": "OUTPUT_TYPES",
    "output_category": "OUTPUT_CATEGORIES",
    "assembly": "ASSEMBLIES",
    "life_stage": "LIFE_STAGES",
    "replication_type": "REPLICATION_TYPES",
}
# Tools that send these filters to the ENCODE portal, which matches them exactly. The tracker
# tools (encode_list_tracked, ...) share the parameter names but match substrings locally.
PORTAL_TOOLS = {
    "encode_search_experiments",
    "encode_search_files",
    "encode_list_files",
    "encode_batch_download",
    "encode_get_facets",
}

CALL_RE = re.compile(r"\b(encode_[a-z_]+)\s*\(")
KEYWORD_RE = re.compile(r"\s*([A-Za-z_]\w*)\s*=(?!=)")
STRING_VALUE_RE = re.compile(r"""\s*[A-Za-z_]\w*\s*=\s*(["'])([^"']*)\1\s*$""")
FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
FLAG_RE = re.compile(r"(?<![\w-])--([A-Za-z_]\w*)")
PROFILE_RE = re.compile(r"(?<![\w-])-profile[ =]+([\w,]+)")
# values that are not meant literally: "", "...", "<type>", "csv|tsv", "{accession}"
PLACEHOLDER_RE = re.compile(r"^$|\.\.\.|[<>|{}]")


def literal_values(annotation: ast.expr | None) -> set[str]:
    """String choices of a ``Literal[...]`` annotation (also inside ``Literal[...] | None``)."""
    if annotation is None:
        return set()
    return {
        constant.value
        for node in ast.walk(annotation)
        # both spellings: Literal[...] and typing.Literal[...]
        if isinstance(node, ast.Subscript) and getattr(node.value, "id", getattr(node.value, "attr", "")) == "Literal"
        for constant in ast.walk(node.slice)
        if isinstance(constant, ast.Constant) and isinstance(constant.value, str)
    }


def catalog_values() -> dict[str, set[str]]:
    """Filter parameter -> the values the server lists for it in constants.py."""
    lists = {
        node.targets[0].id: {item.value for item in node.value.elts if isinstance(item, ast.Constant)}
        for node in ast.parse(CONSTANTS.read_text()).body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.List) and isinstance(node.targets[0], ast.Name)
    }
    return {parameter: lists[name] for parameter, name in CATALOGS.items()}


def tool_functions() -> list[ast.AsyncFunctionDef | ast.FunctionDef]:
    return [
        node
        for node in ast.walk(ast.parse(SERVER.read_text()))
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef) and node.name.startswith("encode_")
    ]


def tool_signatures() -> dict[str, dict[str, set[str]]]:
    """Tool name -> parameter name -> allowed string values (empty when the parameter is free-form)."""
    catalogs = catalog_values()
    return {
        node.name: {
            arg.arg: literal_values(arg.annotation)
            or (catalogs.get(arg.arg, set()) if node.name in PORTAL_TOOLS else set())
            for arg in node.args.args + node.args.kwonlyargs
        }
        for node in tool_functions()
    }


def required_parameters() -> dict[str, set[str]]:
    """Tool name -> parameters that have no default."""
    required = {}
    for node in tool_functions():
        positional = node.args.args[: len(node.args.args) - len(node.args.defaults)]
        keyword_only = [arg for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults) if default is None]
        required[node.name] = {arg.arg for arg in positional + keyword_only}
    return required


def positional_parameters() -> dict[str, list[str]]:
    """Tool name -> its parameters in the order positional arguments fill them."""
    return {node.name: [arg.arg for arg in node.args.args] for node in tool_functions()}


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


def check_tool_calls(signatures: dict[str, dict[str, set[str]]], required: dict[str, set[str]]) -> list[str]:
    problems = []
    order = positional_parameters()
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
            parts = [part for part in top_level_arguments(arguments) if part.strip()]
            named = {match.group(1) for match in map(KEYWORD_RE.match, parts) if match}
            unnamed = [part.strip() for part in parts if not KEYWORD_RE.match(part)]
            # "encode_x(...)" and "**filters" say nothing about which parameters are set;
            # a plain positional argument fills the next positional parameter
            elided = any(part.startswith(("...", "*", "…")) for part in unnamed)
            given = named | set(order[tool][: len(unnamed)])
            if not elided and required[tool] - given:
                missing = ", ".join(sorted(required[tool] - given))
                problems.append(f"{where}: {tool}() is called without its required {missing}")
            for argument in parts:
                keyword = KEYWORD_RE.match(argument)
                if not keyword:
                    continue
                name = keyword.group(1)
                if name not in signatures[tool]:
                    accepted = ", ".join(sorted(signatures[tool]))
                    problems.append(f"{where}: {tool}() has no parameter '{name}' (accepts: {accepted})")
                    continue
                value = STRING_VALUE_RE.match(argument)
                choices = signatures[tool][name]
                if value and choices and value.group(2) not in choices and not PLACEHOLDER_RE.search(value.group(2)):
                    listed = len(choices) <= 8 or name not in CATALOGS
                    accepted = ", ".join(sorted(choices)) if listed else f"the values in {CATALOGS[name]}"
                    problems.append(f'{where}: {tool}({name}="{value.group(2)}") is not accepted (choices: {accepted})')
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


BLOCK_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.S)  # any info string: ```R, ```json, ```bash
JSON_TOKEN_RE = re.compile(r'"((?:[^"\\]|\\.)*)"\s*(:)?|[{}]')
FIELD_NAME_RE = re.compile(r"[a-z_][a-z0-9_]*")


def server_field_names() -> set[str]:
    """Names the server can emit as a JSON key.

    Model fields, keys of dict literals and ``dict(key=...)`` calls, keys assigned with
    ``result["key"] = ...`` or ``setdefault("key", ...)``, and SQLite column names and aliases
    (rows are returned as dicts). Other string literals (messages, URLs, filter values) do not count.
    """
    names: set[str] = set()
    for source in (ROOT / "src" / "encode_connector").rglob("*.py"):
        text = source.read_text()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.ClassDef):
                names |= {
                    field.target.id
                    for field in node.body
                    if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name)
                }
            elif isinstance(node, ast.Dict):
                names |= {
                    key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
            elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    names.add(node.slice.value)
            elif isinstance(node, ast.Call):
                called = getattr(node.func, "id", getattr(node.func, "attr", ""))
                if called == "dict":
                    names |= {keyword.arg for keyword in node.keywords if keyword.arg}
                elif called == "setdefault" and node.args and isinstance(node.args[0], ast.Constant):
                    names.add(str(node.args[0].value))
        names |= set(re.findall(r"^\s+([a-z_][a-z0-9_]*)\s+(?:TEXT|INTEGER|REAL|BLOB)\b", text, re.M))
        names |= set(re.findall(r"\)\s+[Aa][Ss]\s+([a-z_][a-z0-9_]*)", text))
    return names


def example_keys(body: str):
    """Yield (key, ancestors) for each object key in JSON-like text, tolerating ``...`` gaps."""
    stack: list[str | None] = []
    pending: str | None = None
    for token in JSON_TOKEN_RE.finditer(body):
        text = token.group(0)
        if text == "{":
            stack.append(pending)
            pending = None
        elif text == "}":
            if stack:
                stack.pop()
        elif token.group(2):
            pending = token.group(1)
            yield pending, [name for name in stack if name]


def check_output_examples(known: set[str]) -> list[str]:
    problems = []
    catalogs = catalog_values()
    catalog_value_re = re.compile(rf'"({"|".join(catalogs)})"\s*:\s*"([^"]*)"')
    # arrays: facet counts ("assay_title": [{"term": "total RNA-seq", "count": 12}, ...]) and
    # plain lists ("assembly": ["GRCh38"])
    facet_re = re.compile(rf'"({"|".join(catalogs)})"\s*:\s*\[(.*?)\]', re.S)
    term_re = re.compile(r'"term"\s*:\s*"([^"]*)"')
    for doc in sorted(SKILLS.rglob("*.md")):
        text = doc.read_text()
        previous_tool, previous_end = None, 0
        for block in BLOCK_RE.finditer(text):
            language, body = block.groups()
            # "directly follows": only a short lead-in such as "Expected output:" in between,
            # and no new heading. JSON further away documents something else (a log format,
            # another service's API).
            gap = text[previous_end : block.start()]
            if language.strip().lower() == "json" and previous_tool and len(gap) < 200 and "\n#" not in gap:
                line = text.count("\n", 0, block.start()) + 1
                for key, ancestors in example_keys(body):
                    # counts keyed by data values (facets, by_assay, ...) are not field names
                    if any(name == "facets" or name.startswith("by_") for name in ancestors):
                        continue
                    if FIELD_NAME_RE.fullmatch(key) and key not in known:
                        where = f"{doc.relative_to(ROOT)}:{line}"
                        problems.append(f"{where}: {previous_tool}() output has no field '{key}'")
                # a value shown for a filter field must be one ENCODE uses, so it can be searched for
                shown = catalog_value_re.findall(body)
                for field, items in facet_re.findall(body):
                    if "{" in items:  # facet objects
                        shown += [(field, term) for term in term_re.findall(items)]
                    else:  # plain values: "assembly": ["GRCh38", "mm10"]
                        shown += [(field, item) for item in re.findall(r'"([^"]*)"', items)]
                for field, value in shown:
                    if value not in catalogs[field] and not PLACEHOLDER_RE.search(value):
                        where = f"{doc.relative_to(ROOT)}:{line}"
                        problems.append(f'{where}: "{field}": "{value}" is not a value in {CATALOGS[field]}')
            calls = CALL_RE.findall(body)
            previous_tool, previous_end = (calls[-1] if calls else None), block.end()
    return problems


def main() -> int:
    problems = check_tool_calls(tool_signatures(), required_parameters()) + check_pipeline_examples()
    problems += check_output_examples(server_field_names())
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
