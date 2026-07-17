"""章节切块：每块保留章节/小节出处，供检索引用精确到块级。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .loader import Chapter

MAX_CHUNK_CHARS = 1200


@dataclass(frozen=True)
class Chunk:
    chapter_id: str
    chapter_title: str
    heading: str
    anchor: str
    text: str


def slugify(heading: str) -> str:
    """锚点 slug：小写、空白转连字符、保留中文与字母数字。api 渲染与前端跳转共用。"""
    slug = re.sub(r"\s+", "-", heading.strip().lower())
    return re.sub(r"[^\w\u4e00-\u9fff-]", "", slug)


def _split_long(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        if current and len(current) + len(paragraph) + 2 > max_chars:
            parts.append(current.strip())
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current.strip():
        parts.append(current.strip())
    return parts


def split_chapter(chapter: Chapter) -> list[Chunk]:
    sections: list[tuple[str, list[str]]] = [(chapter.title, [])]
    in_code = False
    for line in chapter.markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("## "):
            sections.append((line[3:].strip(), []))
            continue
        if not in_code and line.startswith("# "):
            continue  # H1 已作为章节标题元数据
        sections[-1][1].append(line)

    chunks: list[Chunk] = []
    for heading, lines in sections:
        text = "\n".join(lines).strip()
        if not text:
            continue
        for part in _split_long(text):
            chunks.append(
                Chunk(
                    chapter_id=chapter.id,
                    chapter_title=chapter.title,
                    heading=heading,
                    anchor=slugify(heading),
                    text=part,
                )
            )
    return chunks
