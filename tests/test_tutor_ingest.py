from pathlib import Path

from tutor.ingest.chunker import slugify, split_chapter
from tutor.ingest.loader import load_chapters


def test_load_chapters_covers_numbered_and_appendix():
    chapters = load_chapters(Path("docs"))
    ids = [chapter.id for chapter in chapters]
    assert "00" in ids and "13" in ids and "setup" in ids and "glossary" in ids
    ch05 = next(chapter for chapter in chapters if chapter.id == "05")
    assert "LangGraph" in ch05.title
    # 正文按编号在前，附录按 setup → glossary → reading-list → references 排列
    assert ids.index("13") < ids.index("setup") < ids.index("glossary") < ids.index("reading-list")


def test_split_chapter_keeps_metadata_and_limits_size():
    chapters = load_chapters(Path("docs"))
    ch05 = next(chapter for chapter in chapters if chapter.id == "05")
    chunks = split_chapter(ch05)
    assert all(chunk.chapter_id == "05" for chunk in chunks)
    assert any("Checkpoint" in chunk.heading for chunk in chunks)
    assert all(len(chunk.text) <= 1600 for chunk in chunks)
    assert all(chunk.anchor == slugify(chunk.heading) for chunk in chunks)


def test_slugify_keeps_chinese():
    assert slugify("5.5 Checkpoint：可恢复的关键") == "55-checkpoint可恢复的关键"
