from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from config import CATEGORIES


class ClassificationResult(BaseModel):
    category: str = Field(
        description=(
            "Exactly one of: citations, development, ideas, notes, background, "
            "methods, data_sources, counterarguments"
        )
    )
    confidence: str = Field(description="Classification confidence: high, medium, or low")
    reasoning: str = Field(description="One or two sentences explaining why this category fits best")
    suggested_tags: list[str] = Field(description="2-5 short lowercase tags for this entry")
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


def classify_entry(title: str, content: str, source: str = "", provider: str = "openai") -> ClassificationResult:
    from agents.llm_factory import get_llm

    categories_text = "\n".join(
        f"- {key}: {info['description']}" for key, info in CATEGORIES.items()
    )

    llm = get_llm(provider=provider, max_tokens=512)
    structured_llm = llm.with_structured_output(ClassificationResult)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", "Title: {title}\n\nContent:\n{content}\n\nSource (if any): {source}"),
    ])

    chain = prompt | structured_llm
    return chain.invoke({
        "categories": categories_text,
        "title": title,
        "content": content[:4000],
        "source": source or "Not provided",
    })
