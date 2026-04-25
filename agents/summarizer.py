# Superseded by agents/report_generator.py for the Django web app.
# Kept for potential CLI or notebook use.

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


_SYSTEM = """You are a research synthesis assistant. Given a collection of research entries,
produce a structured synthesis on the user's topic. Be analytical and direct."""


def build_summarizer(provider: str = "openai"):
    from agents.llm_factory import get_llm
    llm = get_llm(provider=provider, max_tokens=2048)
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", "Topic: {topic}\n\nEntries:\n\n{entries}"),
    ])
    return prompt | llm | StrOutputParser()
