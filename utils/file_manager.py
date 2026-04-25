import json
import re
from datetime import datetime
from pathlib import Path

from config import CATEGORIES, DATA_DIR, INDEX_FILE


class FileManager:
    def __init__(self):
        for cat_info in CATEGORIES.values():
            cat_info["folder"].mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not INDEX_FILE.exists():
            INDEX_FILE.write_text(json.dumps([], indent=2))

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def save_research(
        self,
        title: str,
        content: str,
        category: str,
        source: str = "",
        tags: list[str] = None,
        classification_reasoning: str = "",
    ) -> Path:
        tags = tags or []
        folder: Path = CATEGORIES[category]["folder"]
        slug = self._slugify(title)
        filepath = self._unique_path(folder, slug)

        date_str = datetime.now().strftime("%Y-%m-%d")
        tags_yaml = ", ".join(f'"{t}"' for t in tags)

        md = f"""---
title: "{title}"
date: {date_str}
category: {category}
source: "{source}"
tags: [{tags_yaml}]
---

# {title}

**Date Added**: {date_str}
**Category**: {CATEGORIES[category]['label']}
**Source**: {source or "—"}
**Tags**: {", ".join(tags) or "—"}

---

{content}
"""
        filepath.write_text(md, encoding="utf-8")
        self._update_index(title, category, source, tags, filepath, date_str)
        return filepath

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def list_by_category(self, category: str) -> list[dict]:
        index = self._load_index()
        return [e for e in index if e["category"] == category]

    def list_all(self) -> list[dict]:
        return self._load_index()

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        results = []
        for entry in self._load_index():
            haystack = (
                entry["title"].lower()
                + " "
                + " ".join(entry.get("tags", []))
                + " "
                + entry.get("source", "").lower()
            )
            if q in haystack:
                results.append(entry)
        return results

    def read_file(self, filepath: str) -> str:
        return Path(filepath).read_text(encoding="utf-8")

    def get_entries_for_summary(self, topic: str) -> list[dict]:
        """Return entries whose title/tags are relevant to a topic, with content."""
        q = topic.lower()
        results = []
        for entry in self._load_index():
            haystack = (
                entry["title"].lower()
                + " "
                + " ".join(entry.get("tags", []))
            )
            if q in haystack:
                try:
                    content = Path(entry["filepath"]).read_text(encoding="utf-8")
                except FileNotFoundError:
                    content = "(file not found)"
                results.append({**entry, "content": content})
        return results

    def get_all_entries_with_content(self) -> list[dict]:
        results = []
        for entry in self._load_index():
            try:
                content = Path(entry["filepath"]).read_text(encoding="utf-8")
            except FileNotFoundError:
                content = "(file not found)"
            results.append({**entry, "content": content})
        return results

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _load_index(self) -> list[dict]:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    def _update_index(
        self,
        title: str,
        category: str,
        source: str,
        tags: list[str],
        filepath: Path,
        date_str: str,
    ):
        index = self._load_index()
        index.append({
            "title": title,
            "category": category,
            "source": source,
            "tags": tags,
            "filepath": str(filepath),
            "date": date_str,
        })
        INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")

    @staticmethod
    def _slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        return text[:60].strip("-") or "entry"

    @staticmethod
    def _unique_path(folder: Path, slug: str) -> Path:
        candidate = folder / f"{slug}.md"
        counter = 1
        while candidate.exists():
            candidate = folder / f"{slug}-{counter}.md"
            counter += 1
        return candidate
