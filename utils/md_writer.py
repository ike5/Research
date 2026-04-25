"""Write Entry and Report objects to portable markdown files."""
import re
from datetime import datetime
from pathlib import Path


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60].strip("-") or "entry"


def _unique_path(folder: Path, slug: str, ext: str = ".md") -> Path:
    candidate = folder / f"{slug}{ext}"
    n = 1
    while candidate.exists():
        candidate = folder / f"{slug}-{n}{ext}"
        n += 1
    return candidate


def write_entry_md(entry) -> Path:
    from django.conf import settings

    folder = Path(settings.RESEARCH_DATA_DIR) / entry.category.slug
    folder.mkdir(parents=True, exist_ok=True)

    slug = _slugify(entry.title)
    filepath = _unique_path(folder, slug)

    tags = ", ".join(t.name for t in entry.tags.all())
    links = "; ".join(
        f"{l.get_relationship_display()} → {l.to_entry.title}"
        for l in entry.outgoing_links.select_related("to_entry").all()
    )
    date_str = entry.created_at.strftime("%Y-%m-%d") if entry.created_at else datetime.now().strftime("%Y-%m-%d")

    content = f"""---
title: "{entry.title}"
date: {date_str}
category: {entry.category.slug}
source: "{entry.source}"
source_url: "{entry.source_url}"
tags: [{tags}]
entry_id: {entry.pk}
llm_provider: {entry.llm_provider}
confidence: {entry.confidence}
---

# {entry.title}

**Date**: {date_str}
**Category**: {entry.category.name}
**Source**: {entry.source or "—"}
**Tags**: {tags or "—"}
**Links**: {links or "—"}

---

{entry.content}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def write_report_md(report) -> Path:
    from django.conf import settings

    folder = Path(settings.RESEARCH_DATA_DIR) / "reports"
    folder.mkdir(parents=True, exist_ok=True)

    slug = _slugify(report.title)
    filepath = _unique_path(folder, slug)

    date_str = report.created_at.strftime("%Y-%m-%d") if report.created_at else datetime.now().strftime("%Y-%m-%d")
    entry_titles = "\n".join(
        f"- [{e.title}] ({e.category.name})" for e in report.entries.select_related("category").all()
    )

    content = f"""---
title: "{report.title}"
topic: "{report.topic}"
date: {date_str}
llm_provider: {report.llm_provider}
report_id: {report.pk}
---

# {report.title}

**Topic**: {report.topic}
**Generated**: {date_str}
**Provider**: {report.llm_provider}

## Entries Used

{entry_titles or "—"}

---

{report.content}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath
