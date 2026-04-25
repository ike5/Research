from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


_SYSTEM = """You are a research synthesis assistant for a technical academic researcher
working in both a postdoc and startup context. Your reports must be rigorous, direct,
and immediately useful.

Structure every report exactly as follows (use markdown headings):

## Overview
2–3 sentences summarising the current landscape on the topic.

## Key Themes
Bullet points of recurring themes and patterns found across the entries.

## Established Work
What prior literature and citations establish. Draw from entries in the
Citations, Background, and Methods categories.

## Active Development
What the researcher is currently building, arguing, or experimenting with.
Draw from Development and Notes entries.

## Counterarguments & Limitations
Opposing views, open challenges, and known limitations.
Draw from Counterarguments entries and tensions visible in other entries.

## Data & Methods
Key datasets and methodological approaches relevant to the topic.
Draw from Data Sources and Methods entries.

## Open Questions & Ideas
Unresolved gaps, tensions between entries, and ideas worth pursuing.
Draw from Ideas entries and cross-entry analysis.

## Suggested Next Steps
3–5 concrete, prioritised actions the researcher should take based on the current state.

---
Guidelines:
- Cross-reference entries explicitly when they relate to each other.
- Be analytical, not just descriptive. Point out tensions and gaps.
- Prioritise depth over completeness for well-covered areas.
- Keep the tone academic but direct."""


def generate_report(topic: str, entries: list, provider: str = "openai") -> str:
    from agents.llm_factory import get_llm

    llm = get_llm(provider=provider, max_tokens=4096)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        (
            "human",
            "Topic: {topic}\n\n"
            "Research entries ({count} total across all categories):\n\n"
            "{entries}\n\n"
            "Generate the structured research report.",
        ),
    ])

    chain = prompt | llm | StrOutputParser()

    formatted_entries = _format_entries(entries)
    return chain.invoke({
        "topic": topic,
        "count": len(entries),
        "entries": formatted_entries,
    })


def _format_entries(entries: list) -> str:
    parts = []
    for i, entry in enumerate(entries, 1):
        tags = ", ".join(t.name for t in entry.tags.all()) if hasattr(entry, "tags") else ""
        links = _format_links(entry)
        parts.append(
            f"--- Entry {i} ---\n"
            f"Title: {entry.title}\n"
            f"Category: {entry.category.name}\n"
            f"Source: {entry.source or '—'}\n"
            f"Tags: {tags or '—'}\n"
            f"Links: {links or '—'}\n\n"
            f"{entry.content[:2000]}"
            f"{'…[truncated]' if len(entry.content) > 2000 else ''}"
        )
    return "\n\n".join(parts)


def _format_links(entry) -> str:
    try:
        links = entry.outgoing_links.select_related("to_entry").all()
        return "; ".join(f"{l.get_relationship_display()} '{l.to_entry.title}'" for l in links)
    except Exception:
        return ""
