"""
curator/scaffolder.py

Automated scaffolding generator for Learn & Build blueprints.
Parses Section 4 ("Production-Ready Scaffolding Boilerplate") from any blueprint
and generates clean, runnable starter source files in a target workspace directory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


class ScaffoldFile(NamedTuple):
    filename: str
    content: str
    language: str


class ScaffoldResult(NamedTuple):
    slug: str
    target_dir: Path
    files: list[ScaffoldFile]
    instructions: str


def _extract_section_4(markdown_text: str) -> str:
    """Extract content strictly within Section 4 of the blueprint."""
    pattern = re.compile(
        r"## 4\.\s+(?:Production-Ready Scaffolding|Copy-Paste Code)[^\n]*\n([\s\S]*?)(?=\n## 5\.|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(markdown_text)
    if match:
        return match.group(1).strip()
    return ""


def _infer_filename_for_code(lang: str, code: str, slug: str, block_index: int) -> str:
    """Infer the most idiomatic file path and name for the code block."""
    lang_clean = lang.lower().strip()

    # Java inference
    if lang_clean == "java":
        pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_.]+);", code, re.MULTILINE)
        class_match = re.search(r"public\s+(?:final\s+)?(?:class|interface|enum)\s+([A-Za-z0-9_]+)", code)
        class_name = class_match.group(1) if class_match else f"Demo{block_index or ''}"
        if pkg_match:
            pkg_path = pkg_match.group(1).replace(".", "/")
            return f"src/main/java/{pkg_path}/{class_name}.java"
        return f"{class_name}.java"

    # Rust inference
    if lang_clean in ("rust", "rs"):
        if "fn main" in code:
            return "src/main.rs"
        if "pub mod" in code or "pub fn" in code:
            return "src/lib.rs"
        return f"src/{slug.replace('-', '_')}.rs"

    # Go inference
    if lang_clean in ("go", "golang"):
        if "func main" in code:
            return "main.go"
        return f"{slug}.go"

    # Python inference
    if lang_clean in ("python", "py"):
        if "__main__" in code:
            return "main.py"
        return f"{slug.replace('-', '_')}.py"

    # C / C++ inference
    if lang_clean in ("c", "h"):
        if code.strip().startswith(("#ifndef", "#pragma once")) or lang_clean == "h":
            return f"include/{slug}.h"
        return "main.c"
    if lang_clean in ("cpp", "cc", "cxx", "hpp"):
        if code.strip().startswith(("#ifndef", "#pragma once")) or lang_clean == "hpp":
            return f"include/{slug}.hpp"
        return "main.cpp"

    # Shell script inference
    if lang_clean in ("bash", "sh", "shell"):
        return "run.sh"

    # TOML / Config inference
    if lang_clean == "toml" or "[package]" in code:
        return "Cargo.toml"

    # JSON inference
    if lang_clean == "json":
        return "config.json"

    # Default fallback
    ext = lang_clean if lang_clean and len(lang_clean) <= 4 else "txt"
    return f"{slug}_scaffold_{block_index}.{ext}"


def extract_scaffold_files(markdown_text: str, slug: str) -> list[ScaffoldFile]:
    """Parse all code blocks in Section 4 into ScaffoldFile objects."""
    sec4_text = _extract_section_4(markdown_text)
    if not sec4_text:
        return []

    # Find fenced code blocks
    code_pattern = re.compile(r"```([a-zA-Z0-9_\-+]*)\n([\s\S]*?)```", re.MULTILINE)
    blocks = code_pattern.findall(sec4_text)

    files: list[ScaffoldFile] = []
    for idx, (lang, code) in enumerate(blocks, start=1):
        clean_code = code.strip()
        if not clean_code:
            continue
        filename = _infer_filename_for_code(lang, clean_code, slug, idx)
        files.append(ScaffoldFile(filename=filename, content=clean_code, language=lang or "text"))

    return files


def scaffold_blueprint(blueprint_path: Path, output_dir: Path) -> ScaffoldResult:
    """
    Extract scaffold files from a blueprint and write them into output_dir.
    """
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")

    text = blueprint_path.read_text(encoding="utf-8")
    slug = blueprint_path.stem
    files = extract_scaffold_files(text, slug)

    if not files:
        raise ValueError(f"No code boilerplate blocks found in Section 4 of {blueprint_path.name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: list[Path] = []

    for f in files:
        dest_file = output_dir / f.filename
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.write_text(f.content + "\n", encoding="utf-8")
        generated_paths.append(dest_file)

    # Generate a companion README.md for the scaffold
    readme_path = output_dir / "README.md"
    if not readme_path.exists():
        instructions = (
            f"# Scaffold: {slug}\n\n"
            f"Generated from **Learn & Build** architectural blueprint `{blueprint_path.name}`.\n\n"
            f"## Emitted Files\n"
            + "\n".join(f"- `{f.filename}` ({f.language})" for f in files)
            + "\n\n## Next Steps\n"
            f"Build or run these source files in your active workspace environment.\n"
        )
        readme_path.write_text(instructions, encoding="utf-8")

    return ScaffoldResult(
        slug=slug,
        target_dir=output_dir,
        files=files,
        instructions=f"Emitted {len(files)} source file(s) into {output_dir}",
    )
