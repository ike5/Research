import json
import re

from pydantic import BaseModel, Field, ValidationError
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import CATEGORIES


class ClassificationResult(BaseModel):
    category: str = Field(
        description=(
            "Exactly one of: citations, development, ideas, notes, background, "
            "methods, data_sources, counterarguments"
        )
    )
    confidence: str = Field(
        description="Classification confidence: high, medium, or low"
    )
    reasoning: str = Field(
        description="One or two sentences explaining why this category fits best"
    )
    suggested_tags: list[str] = Field(
        description="2-5 short lowercase tags for this entry"
    )
    suggested_title: str = Field(
        description="A clear, concise title. Improve the given title or generate one if absent."
    )


_SYSTEM = """You are a research organization assistant for a technical academic researcher
(postdoc and startup context). Classify research entries into exactly one category:

{categories}

Decision rules:
- citations: authored by someone else — a paper, study, article, or external resource you are referencing.
- development: your own in-progress research, analysis, experimental notes, or draft arguments.
- ideas: a hypothesis, unexplored question, or seed for a future project you haven't started yet.
- notes: informal observation, quick thought, meeting note, or reflection that doesn't fit elsewhere.
- background: definitions, historical context, theoretical frameworks you are reading to ground your work.
- methods: a methodology, experimental protocol, statistical technique, or procedural approach.
- data_sources: a dataset, database, API, instrument, or source of raw data.
- counterarguments: an opposing view, limitation, criticism, or challenge to your or others' thesis.

Be decisive. When in doubt between two categories, pick the single best fit."""


_HUMAN = "Title: {title}\n\nContent:\n{content}\n\nSource (if any): {source}"

_JSON_INSTRUCTION = (
    "\n\nRespond ONLY with a JSON object matching this schema — no prose, no markdown formatting, "
    "no commentary outside the JSON:\n"
    '{{"category": "...", "confidence": "...", "reasoning": "...", '
    '"suggested_tags": ["..."], "suggested_title": "..."}}'
)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _extract_json(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    if match:
        text = match.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text


def _strip_markdown_inline(obj_str: str) -> str:
    return re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", obj_str)


def _parse_raw(text: str) -> ClassificationResult:
    cleaned = _strip_markdown_inline(text)
    parsed = json.loads(cleaned)
    parsed["suggested_tags"] = [
        t.strip().lower().replace(" ", "-") for t in parsed.get("suggested_tags", [])
    ]
    valid_categories = set(CATEGORIES.keys())
    if parsed.get("category") not in valid_categories:
        for cat in valid_categories:
            if cat in parsed.get("category", "").lower():
                parsed["category"] = cat
                break
    return ClassificationResult(**parsed)


def classify_entry(
    title: str, content: str, source: str = "", provider: str = "openai"
) -> ClassificationResult:
    from agents.llm_factory import get_llm

    categories_text = "\n".join(
        f"- {key}: {info['description']}" for key, info in CATEGORIES.items()
    )

    llm = get_llm(provider=provider, max_tokens=512)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM),
            ("human", _HUMAN),
        ]
    )
    invoke_kwargs = {
        "categories": categories_text,
        "title": title,
        "content": content[:4000],
        "source": source or "Not provided",
    }

    try:
        structured_llm = llm.with_structured_output(ClassificationResult)
        chain = prompt | structured_llm
        return chain.invoke(invoke_kwargs)
    except Exception:
        pass

    chain = prompt | llm | StrOutputParser()
    raw = chain.invoke(invoke_kwargs)
    try:
        json_str = _extract_json(raw)
        return _parse_raw(json_str)
    except (json.JSONDecodeError, ValidationError):
        pass

    fallback_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM + _JSON_INSTRUCTION),
            ("human", _HUMAN),
        ]
    )
    chain = fallback_prompt | llm | StrOutputParser()
    raw = chain.invoke(invoke_kwargs)
    json_str = _extract_json(raw)
    return _parse_raw(json_str)
