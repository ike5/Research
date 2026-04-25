# Research Organizer

An AI-powered research knowledge base for organizing, classifying, and synthesizing academic research materials. Built with Django and LangChain, it leverages LLMs to automatically classify entries, generate synthesis reports, and provide an interactive chat agent for exploring your knowledge graph.

## Features

- **AI-Powered Entry Classification** — Paste text, provide a file path, or enter a URL, and the LLM automatically categorizes, tags, and titles your entry
- **Multi-Source Ingestion** — Add entries from plain text, local files (`.txt`, `.md`, `.pdf`, `.docx`), or URLs (auto-scraped)
- **Inter-Entry Linking** — Connect entries with typed relationships (`supports`, `contradicts`, `extends`, `cites`, `uses`, `challenges`)
- **Research Reports** — AI-generated synthesis reports that aggregate entries into structured markdown with key themes, established work, counterarguments, and open questions
- **AI Chat Agent** — Three modes: *Explore* (Q&A with citations), *Contest* (adversarial peer review), *Edit* (proposes rewrites you can apply directly)
- **Knowledge Graph** — Interactive D3.js force-directed visualization of entries and their relationships
- **Markdown Export** — Every entry and report is saved as a portable markdown file with YAML frontmatter
- **Multi-LLM Support** — Choose between OpenAI (GPT-4o), Anthropic (Claude), or Ollama (local models) per action or per chat session

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x |
| Database | SQLite3 |
| LLM Orchestration | LangChain |
| Data Validation | Pydantic 2.x |
| Frontend | Bootstrap 5.3, D3.js 7 |
| PDF Parsing | pypdf |
| DOCX Parsing | python-docx |
| Web Scraping | BeautifulSoup4, requests |

## Prerequisites

- Python 3.12+
- An LLM provider: an OpenAI API key, an Anthropic API key, or a running [Ollama](https://ollama.ai) instance

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/Research.git
cd Research

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys and preferred LLM provider

# Run database migrations
python manage.py migrate

# Seed default categories
python manage.py setup_research

# Create an admin superuser (optional)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

The app will be available at **http://127.0.0.1:8000/**.

## Configuration

All configuration is handled through a `.env` file (based on `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | `"dev-only-insecure-key-change-in-production"` | Django secret key (change in production!) |
| `DEBUG` | `True` | Django debug mode |
| `LLM_PROVIDER` | `openai` | Default LLM: `openai`, `ollama`, or `anthropic` |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model name |
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-opus-4-7` | Anthropic model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |

### Using Ollama (Local LLM)

1. Install and start [Ollama](https://ollama.ai)
2. Pull a model: `ollama pull llama3.2`
3. Set `LLM_PROVIDER=ollama` in your `.env`
4. No API key needed

## Usage

### Adding Entries

1. Navigate to **Entries → Add Entry**
2. Paste text, provide a local file path, or enter a URL
3. The LLM will classify the entry, suggest a title and tags, and provide classification reasoning
4. Review the AI suggestions and confirm or adjust before saving

### Linking Entries

1. Open any entry and click **Link Entry**
2. Select a target entry and a relationship type (`supports`, `contradicts`, `extends`, `cites`, `uses`, `challenges`)
3. Links form a directed knowledge graph between your research materials

### Generating Reports

1. Navigate to **Reports → Create Report**
2. Select a topic and choose which entries to include
3. The AI generates a structured synthesis report with sections on key themes, established work, counterarguments, open questions, and suggested next steps

### Chatting with Your Knowledge Base

1. Navigate to **Chat → New Session**
2. Choose a mode:
   - **Explore** — Ask questions about your research; the agent cites specific entries
   - **Contest** — An adversarial reviewer challenges your assumptions and arguments
   - **Edit** — The agent proposes concrete rewrites (click to apply directly to entries)
3. Select an LLM provider for the session
4. Chat naturally; the agent has access to your full knowledge base

### Knowledge Graph

Navigate to **Graph** to see an interactive D3.js force-directed visualization of all entries and their relationships. Nodes are colored by category and sized by word count/links.

## Entry Categories

| Slug | Category | Description |
|------|----------|-------------|
| `citations` | Citations & Prior Work | Academic papers and external research |
| `development` | Research Development | Your own active research, analyses, and drafts |
| `ideas` | Research Ideas | Hypotheses and unexplored questions |
| `notes` | Notes & Observations | Quick thoughts and informal reflections |
| `background` | Background & Theory | Theoretical frameworks and foundational concepts |
| `methods` | Methods | Research methodologies and experimental designs |
| `data_sources` | Data Sources | Datasets, databases, and raw data references |
| `counterarguments` | Counterarguments | Opposing views and critical perspectives |

## Project Structure

```
Research/
├── config.py                 # Category definitions and LLM provider config
├── manage.py                  # Django entry point
├── requirements.txt           # Python dependencies
├── research_project/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                      # Main Django app
│   ├── models.py              # Category, Tag, Entry, EntryLink, Report, ChatSession, ChatMessage
│   ├── views.py               # All views
│   ├── forms.py               # Django forms
│   ├── urls.py                # URL routing
│   ├── management/commands/
│   │   └── setup_research.py  # Seed categories command
│   └── templates/core/        # HTML templates
├── agents/                    # LLM agent modules
│   ├── llm_factory.py         # Create LangChain chat models
│   ├── classifier.py          # AI entry classifier
│   ├── chat_agent.py          # Conversational agent (explore/contest/edit)
│   ├── report_generator.py   # AI research report synthesizer
│   └── summarizer.py          # Legacy summarizer
├── ingest/                    # Content ingestion
│   ├── file_loader.py         # Load .txt/.md/.pdf/.docx files
│   └── url_loader.py          # Scrape and clean URLs
└── utils/                     # Utilities
    ├── md_writer.py           # Write entries/reports to markdown
    └── file_manager.py        # File-based index utilities
```

## URL Routes

| Path | Purpose |
|------|---------|
| `/` | Dashboard with stats and recent activity |
| `/entries/` | List, search, and filter entries |
| `/entries/add/` | Create a new entry (AI-classified) |
| `/entries/<pk>/` | View entry detail |
| `/entries/<pk>/edit/` | Edit an entry |
| `/entries/<pk>/delete/` | Delete an entry |
| `/entries/<pk>/link/` | Link an entry to another |
| `/category/<slug>/` | Filter entries by category |
| `/reports/` | List all reports |
| `/reports/create/` | Generate an AI synthesis report |
| `/reports/<pk>/` | View a report |
| `/chat/` | List chat sessions |
| `/chat/new/` | Start a new chat session |
| `/chat/<pk>/` | Chat interface |
| `/chat/apply/<msg_pk>/<entry_pk>/` | Apply an AI edit suggestion |
| `/graph/` | Knowledge graph visualization |
| `/admin/` | Django admin interface |

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.