"""把 docs/*.md 读成 Chapter 列表；只扫顶层，spec/计划子目录自然排除。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chapter:
    id: str
    title: str
    path: Path
    markdown: str


def _chapter_id(path: Path) -> str:
    match = re.match(r"^(\d{2})-", path.name)
    return match.group(1) if match else path.stem


def _chapter_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


# 附录没有数字前缀，按教程约定的顺序排在正文章节之后。
_APPENDIX_ORDER = {"setup": 0, "glossary": 1, "reading-list": 2, "references": 3}


def _sort_key(path: Path) -> tuple:
    numbered = re.match(r"^(\d{2})-", path.name)
    if numbered:
        return (0, int(numbered.group(1)))
    return (1, _APPENDIX_ORDER.get(path.stem, 99), path.stem)


def load_chapters(docs_dir: Path) -> list[Chapter]:
    chapters = []
    for path in sorted(docs_dir.glob("*.md"), key=_sort_key):
        markdown = path.read_text(encoding="utf-8")
        chapters.append(
            Chapter(
                id=_chapter_id(path),
                title=_chapter_title(markdown, path.stem),
                path=path,
                markdown=markdown,
            )
        )
    return chapters
