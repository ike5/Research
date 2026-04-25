from pathlib import Path

BASE_DIR = Path(__file__).parent

CATEGORIES = {
    "citations": {
        "label": "Citations & Prior Work",
        "description": "Academic papers, university studies, and external research by others that supports or is relevant to your topic.",
        "icon": "📚",
        "color": "primary",
    },
    "development": {
        "label": "Research Development",
        "description": "Your own active research, analyses, arguments, experimental notes, and drafts you are building.",
        "icon": "🔬",
        "color": "success",
    },
    "ideas": {
        "label": "Research Ideas",
        "description": "Hypotheses, unexplored questions, and seeds for future or separate research projects.",
        "icon": "💡",
        "color": "warning",
    },
    "notes": {
        "label": "Notes & Observations",
        "description": "Quick thoughts, observations, meeting notes, and informal reflections.",
        "icon": "📝",
        "color": "secondary",
    },
    "background": {
        "label": "Background & Theory",
        "description": "Theoretical frameworks, definitions, historical context, and foundational concepts.",
        "icon": "📖",
        "color": "info",
    },
    "methods": {
        "label": "Methods",
        "description": "Research methodologies, experimental designs, statistical approaches, and procedural notes.",
        "icon": "⚗️",
        "color": "danger",
    },
    "data_sources": {
        "label": "Data Sources",
        "description": "Datasets, databases, APIs, instruments, and raw data references used in research.",
        "icon": "🗄️",
        "color": "dark",
    },
    "counterarguments": {
        "label": "Counterarguments",
        "description": "Opposing views, challenges to your thesis, limitations, and critical perspectives.",
        "icon": "⚖️",
        "color": "danger",
    },
}

LLM_PROVIDERS = ["openai", "ollama", "anthropic"]
