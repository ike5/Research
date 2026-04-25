"""
Conversational agent that answers questions about stored research entries.

Supports three modes:
  explore  — Q&A assistant, cites entry IDs
  contest  — adversarial peer reviewer, challenges assumptions
  edit     — editor, wraps proposed rewrites in [EDIT:{pk}]...[/EDIT] blocks
"""
import re

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ── System prompts ─────────────────────────────────────────────────────────────

_SYSTEM_EXPLORE = """You are a knowledgeable research assistant with full access to the \
researcher's personal knowledge base. The knowledge base is provided below.

Your job:
- Answer questions accurately, drawing only from the provided entries.
- When a claim is grounded in a specific entry, cite it as [Entry #<id>: <title>].
- Point out connections between entries the researcher may not have noticed.
- If the knowledge base does not contain enough information, say so clearly rather than guessing.

Knowledge base:
{context}"""

_SYSTEM_CONTEST = """You are a rigorous academic peer reviewer and devil's advocate. \
The researcher's knowledge base is provided below.

Your job:
- Challenge assumptions, identify logical gaps, and steelman opposing positions.
- Ask hard questions: What evidence is missing? What would falsify this claim?
- Surface tensions or contradictions between entries.
- Be direct and academically rigorous — do not soften criticism.
- When referencing a specific entry, cite it as [Entry #<id>: <title>].

Knowledge base:
{context}"""

_SYSTEM_EDIT = """You are a research editor with access to the researcher's knowledge base.

Your job:
- Help improve the clarity, structure, and rigour of individual entries.
- When proposing a rewrite of an entry, wrap the proposed content in edit markers:
  [EDIT:{entry_pk}]
  <full proposed content here>
  [/EDIT]
- Only one [EDIT] block per response. Do not partially edit — always propose the complete entry text.
- Outside of edit blocks, explain what you changed and why.
- When referencing entries, cite them as [Entry #<id>: <title>].

Knowledge base:
{context}"""

_SYSTEM = {
    "explore": _SYSTEM_EXPLORE,
    "contest": _SYSTEM_CONTEST,
    "edit":    _SYSTEM_EDIT,
}

# ── Context builder ────────────────────────────────────────────────────────────

def _score_entry(entry, keywords: set[str]) -> int:
    haystack = (
        entry.title.lower()
        + " " + " ".join(t.name.lower() for t in entry.tags.all())
        + " " + entry.content[:600].lower()
    )
    return sum(1 for kw in keywords if kw in haystack)


def _select_entries(message: str, all_entries) -> list:
    """Return the most relevant entries for the user message (no embeddings needed)."""
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to",
                 "and", "or", "for", "with", "this", "that", "it", "my", "me",
                 "can", "do", "does", "how", "what", "why", "when", "which", "who"}
    keywords = {w for w in re.findall(r"[a-z]+", message.lower()) if w not in stopwords and len(w) > 2}

    if not keywords:
        return list(all_entries[:20])

    scored = [(entry, _score_entry(entry, keywords)) for entry in all_entries]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Take top 20 by score, always include entries with score > 0
    top = [e for e, s in scored if s > 0][:20]
    if not top:
        top = [e for e, _ in scored[:10]]

    # Expand with linked entries
    linked_ids = set()
    for entry in top:
        linked_ids.update(entry.outgoing_links.values_list("to_entry_id", flat=True))
        linked_ids.update(entry.incoming_links.values_list("from_entry_id", flat=True))

    linked = [e for e, _ in scored if e.pk in linked_ids and e not in top][:10]
    return top + linked


def _format_context(entries: list) -> str:
    parts = []
    for entry in entries:
        tags = ", ".join(t.name for t in entry.tags.all())
        links = "; ".join(
            f"{l.get_relationship_display()} Entry #{l.to_entry_id}"
            for l in entry.outgoing_links.select_related("to_entry").all()
        )
        parts.append(
            f"[Entry #{entry.pk}: {entry.title}]\n"
            f"Category: {entry.category.name} | Source: {entry.source or '—'} | Tags: {tags or '—'}\n"
            f"Links: {links or '—'}\n\n"
            f"{entry.content[:2500]}"
            f"{'…[truncated]' if len(entry.content) > 2500 else ''}"
        )
    return "\n\n---\n\n".join(parts)


# ── Edit block parser ──────────────────────────────────────────────────────────

_EDIT_RE = re.compile(r"\[EDIT:(\d+)\](.*?)\[/EDIT\]", re.DOTALL)
_CITE_RE = re.compile(r"\[Entry #(\d+):")


def _parse_response(reply: str) -> dict:
    edit_blocks = [
        {"entry_pk": int(m.group(1)), "proposed_content": m.group(2).strip()}
        for m in _EDIT_RE.finditer(reply)
    ]
    cited_ids = [int(i) for i in _CITE_RE.findall(reply)]
    return {"edit_blocks": edit_blocks, "cited_entry_ids": list(set(cited_ids))}


# ── Public API ─────────────────────────────────────────────────────────────────

def chat(session_id: int, user_message: str) -> dict:
    """
    Process one user turn. Saves messages to DB and returns:
        {
            "reply": str,
            "reply_html": str  (markdown → html),
            "cited_entry_ids": [int],
            "edit_blocks": [{"entry_pk": int, "proposed_content": str}],
        }
    """
    import markdown as md_lib
    from django.db.models import Prefetch

    from core.models import ChatMessage, ChatSession, Entry, Tag

    session = ChatSession.objects.get(pk=session_id)
    provider = session.llm_provider or None

    # Load all entries with prefetched relations (one DB round-trip)
    all_entries = list(
        Entry.objects.select_related("category")
        .prefetch_related("tags", "outgoing_links", "incoming_links")
        .order_by("-created_at")
    )

    relevant = _select_entries(user_message, all_entries)
    context = _format_context(relevant)

    # Reconstruct history
    history = []
    for msg in session.messages.order_by("created_at"):
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))

    # Build and invoke chain
    from agents.llm_factory import get_llm

    system_tpl = _SYSTEM.get(session.mode, _SYSTEM["explore"])
    system_text = system_tpl.format(context=context)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{message}"),
    ])
    chain = prompt | get_llm(provider=provider, max_tokens=2048) | StrOutputParser()

    reply = chain.invoke({"system": system_text, "history": history, "message": user_message})

    # Parse structured data from reply
    parsed = _parse_response(reply)

    # Persist user message
    user_msg = ChatMessage.objects.create(session=session, role="user", content=user_message)

    # Persist assistant message
    has_edit = bool(parsed["edit_blocks"])
    ai_msg = ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=reply,
        has_edit_suggestion=has_edit,
    )
    if parsed["cited_entry_ids"]:
        from core.models import Entry as E
        cited = E.objects.filter(pk__in=parsed["cited_entry_ids"])
        ai_msg.cited_entries.set(cited)

    # Touch session.updated_at
    session.save(update_fields=["updated_at"])

    reply_html = md_lib.markdown(reply, extensions=["fenced_code", "tables"])
    return {
        "reply": reply,
        "reply_html": reply_html,
        "cited_entry_ids": parsed["cited_entry_ids"],
        "edit_blocks": parsed["edit_blocks"],
        "ai_message_pk": ai_msg.pk,
    }
