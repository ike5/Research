from django import forms
from .models import Entry, EntryLink, Report, Category, ChatSession


LLM_CHOICES = [
    ("openai", "OpenAI (GPT-4o)"),
    ("ollama", "Ollama (local)"),
    ("anthropic", "Anthropic (Claude)"),
]

ENTRY_SELECTION_CHOICES = [
    ("topic", "Entries matching the topic (auto)"),
    ("all", "All entries"),
    ("manual", "Select entries manually"),
]


class EntryInputForm(forms.Form):
    """Step 1 — raw input from user."""

    title = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Leave blank to auto-generate"}),
        help_text="Leave blank and the AI will suggest one.",
    )
    text_content = forms.CharField(
        required=False,
        label="Paste research text",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 10, "placeholder": "Paste text here…"}),
    )
    file_path = forms.CharField(
        max_length=500,
        required=False,
        label="File path",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "/path/to/paper.pdf  or  paper.txt"}),
        help_text="Supports .txt  .md  .pdf  .docx",
    )
    source_url = forms.URLField(
        required=False,
        label="Source URL",
        widget=forms.URLInput(attrs={"class": "form-control", "placeholder": "https://arxiv.org/abs/…"}),
        help_text="The page will be scraped automatically.",
    )
    source = forms.CharField(
        max_length=500,
        required=False,
        label="Source / citation",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Author, Institution, Year"}),
    )
    tags = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "ml, transformers, 2024"}),
        help_text="Comma-separated tags.",
    )
    llm_provider = forms.ChoiceField(
        choices=LLM_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def clean(self):
        data = super().clean()
        if not any([data.get("text_content"), data.get("file_path"), data.get("source_url")]):
            raise forms.ValidationError("Provide at least one of: text, file path, or URL.")
        return data


class EntryConfirmForm(forms.ModelForm):
    """Step 2 — review AI classification, adjust, and save."""

    tags_input = forms.CharField(
        max_length=500,
        required=False,
        label="Tags",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "ml, transformers, 2024"}),
        help_text="Comma-separated.",
    )

    class Meta:
        model = Entry
        fields = ["title", "content", "category", "source", "source_url", "classification_reasoning"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 12}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "source": forms.TextInput(attrs={"class": "form-control"}),
            "source_url": forms.URLInput(attrs={"class": "form-control"}),
            "classification_reasoning": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class EntryLinkForm(forms.ModelForm):
    class Meta:
        model = EntryLink
        fields = ["to_entry", "relationship", "note"]
        widgets = {
            "to_entry": forms.Select(attrs={"class": "form-select"}),
            "relationship": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional note about this link…"}),
        }

    def __init__(self, *args, exclude_entry=None, **kwargs):
        super().__init__(*args, **kwargs)
        if exclude_entry:
            self.fields["to_entry"].queryset = Entry.objects.exclude(pk=exclude_entry.pk).order_by("title")


class ReportForm(forms.Form):
    title = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "My Research Summary — Q2 2025"}),
    )
    topic = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. transformer attention mechanisms"}),
        help_text="The AI will synthesize entries relevant to this topic.",
    )
    entry_selection = forms.ChoiceField(
        choices=ENTRY_SELECTION_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="topic",
    )
    selected_entries = forms.ModelMultipleChoiceField(
        queryset=Entry.objects.all().order_by("-created_at"),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )
    llm_provider = forms.ChoiceField(
        choices=LLM_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class ChatSessionForm(forms.ModelForm):
    class Meta:
        model = ChatSession
        fields = ["title", "mode", "llm_provider"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Questions about my methods chapter",
            }),
            "mode": forms.Select(attrs={"class": "form-select"}),
            "llm_provider": forms.Select(
                choices=[("openai", "OpenAI (GPT-4o)"), ("ollama", "Ollama (local)"), ("anthropic", "Anthropic (Claude)")],
                attrs={"class": "form-select"},
            ),
        }
