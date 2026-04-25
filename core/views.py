import json

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Count, Q
import markdown as md_lib

from .models import Category, Entry, EntryLink, Report, Tag, ChatSession, ChatMessage
from .forms import EntryInputForm, EntryConfirmForm, EntryLinkForm, ReportForm, ChatSessionForm


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_content(data: dict) -> tuple[str, str, str]:
    """Return (content, source_url, inferred_source) from cleaned form data."""
    text = (data.get("text_content") or "").strip()
    file_path = (data.get("file_path") or "").strip()
    url = (data.get("source_url") or "").strip()

    if text:
        return text, url, data.get("source", "")

    if file_path:
        from ingest.file_loader import load_file
        content = load_file(file_path)
        return content, url, file_path

    if url:
        from ingest.url_loader import load_url
        content, _ = load_url(url)
        return content, url, url

    return "", "", ""


def _save_tags(entry: Entry, tags_raw: str):
    """Parse comma-separated tags and attach to entry."""
    for name in [t.strip() for t in tags_raw.split(",") if t.strip()]:
        tag, _ = Tag.objects.get_or_create(name=name, defaults={"slug": name.lower().replace(" ", "-")[:50]})
        entry.tags.add(tag)


# ── Home ───────────────────────────────────────────────────────────────────────

def home(request):
    categories = Category.objects.annotate(entry_count=Count("entries")).order_by("name")
    recent_entries = Entry.objects.select_related("category").order_by("-created_at")[:8]
    recent_reports = Report.objects.order_by("-created_at")[:5]
    total_entries = Entry.objects.count()
    total_reports = Report.objects.count()
    return render(request, "core/home.html", {
        "categories": categories,
        "recent_entries": recent_entries,
        "recent_reports": recent_reports,
        "total_entries": total_entries,
        "total_reports": total_reports,
    })


# ── Entry list / category ──────────────────────────────────────────────────────

class EntryListView(ListView):
    model = Entry
    template_name = "core/entry_list.html"
    context_object_name = "entries"
    paginate_by = 20

    def get_queryset(self):
        qs = Entry.objects.select_related("category").prefetch_related("tags")
        q = self.request.GET.get("q", "").strip()
        cat_slug = self.request.GET.get("category", "").strip()
        tag_slug = self.request.GET.get("tag", "").strip()

        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(content__icontains=q) | Q(source__icontains=q)
            ).distinct()
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["current_category"] = self.request.GET.get("category", "")
        ctx["current_tag"] = self.request.GET.get("tag", "")
        ctx["tags"] = Tag.objects.order_by("name")
        return ctx


def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    entries = Entry.objects.filter(category=category).select_related("category").prefetch_related("tags")
    return render(request, "core/entry_list.html", {
        "entries": entries,
        "active_category": category,
        "q": "",
        "current_category": slug,
        "current_tag": "",
        "tags": Tag.objects.order_by("name"),
    })


# ── Entry add (two-step) ───────────────────────────────────────────────────────

def entry_add(request):
    if request.method == "POST":
        step = request.POST.get("step", "1")

        # ── Step 1: classify ──────────────────────────────────────────────────
        if step == "1":
            form = EntryInputForm(request.POST)
            if form.is_valid():
                try:
                    content, source_url, inferred_source = _extract_content(form.cleaned_data)
                    if not content:
                        messages.error(request, "Could not extract content. Check your input.")
                        return render(request, "core/entry_add.html", {"step": "1", "form": form})

                    title = form.cleaned_data.get("title", "").strip()
                    source = form.cleaned_data.get("source", "").strip() or inferred_source
                    provider = form.cleaned_data.get("llm_provider", "openai")

                    from agents.classifier import classify_entry
                    result = classify_entry(title=title or "Untitled", content=content, source=source, provider=provider)

                    category = Category.objects.filter(slug=result.category).first()
                    confirm_form = EntryConfirmForm(initial={
                        "title": result.suggested_title or title,
                        "content": content,
                        "category": category,
                        "source": source,
                        "source_url": source_url,
                        "classification_reasoning": result.reasoning,
                    })
                    return render(request, "core/entry_add.html", {
                        "step": "2",
                        "confirm_form": confirm_form,
                        "result": result,
                        "provider": provider,
                        "tags_prefill": form.cleaned_data.get("tags", ""),
                        "category_color": category.color if category else "secondary",
                    })
                except Exception as exc:
                    messages.error(request, f"Classification failed: {exc}")
            return render(request, "core/entry_add.html", {"step": "1", "form": form})

        # ── Step 2: save ──────────────────────────────────────────────────────
        elif step == "2":
            confirm_form = EntryConfirmForm(request.POST)
            if confirm_form.is_valid():
                entry = confirm_form.save(commit=False)
                entry.confidence = request.POST.get("confidence", "")
                entry.llm_provider = request.POST.get("provider", "")
                entry.save()

                _save_tags(entry, request.POST.get("tags_input", ""))

                from utils.md_writer import write_entry_md
                entry.md_filepath = str(write_entry_md(entry))
                entry.save(update_fields=["md_filepath"])

                messages.success(request, f"Entry '{entry.title}' saved.")
                return redirect("core:entry_detail", pk=entry.pk)

            # Re-render step 2 with errors
            return render(request, "core/entry_add.html", {
                "step": "2",
                "confirm_form": confirm_form,
                "provider": request.POST.get("provider", ""),
                "tags_prefill": request.POST.get("tags_input", ""),
            })

    form = EntryInputForm()
    return render(request, "core/entry_add.html", {"step": "1", "form": form})


# ── Entry detail / edit / delete ───────────────────────────────────────────────

class EntryDetailView(DetailView):
    model = Entry
    template_name = "core/entry_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        entry = self.object
        ctx["outgoing_links"] = entry.outgoing_links.select_related("to_entry__category")
        ctx["incoming_links"] = entry.incoming_links.select_related("from_entry__category")
        ctx["content_html"] = md_lib.markdown(entry.content, extensions=["fenced_code", "tables"])
        return ctx


def entry_edit(request, pk):
    entry = get_object_or_404(Entry, pk=pk)
    if request.method == "POST":
        form = EntryConfirmForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()
            _save_tags(entry, request.POST.get("tags_input", ""))
            from utils.md_writer import write_entry_md
            entry.md_filepath = str(write_entry_md(entry))
            entry.save(update_fields=["md_filepath"])
            messages.success(request, "Entry updated.")
            return redirect("core:entry_detail", pk=entry.pk)
    else:
        form = EntryConfirmForm(instance=entry, initial={
            "tags_input": entry.tag_list(),
        })
    return render(request, "core/entry_add.html", {
        "step": "2",
        "confirm_form": form,
        "edit_mode": True,
        "entry": entry,
        "tags_prefill": entry.tag_list(),
    })


def entry_delete(request, pk):
    entry = get_object_or_404(Entry, pk=pk)
    if request.method == "POST":
        title = entry.title
        entry.delete()
        messages.success(request, f"Entry '{title}' deleted.")
        return redirect("core:entry_list")
    return render(request, "core/confirm_delete.html", {"object": entry, "type": "entry"})


# ── Entry linking ──────────────────────────────────────────────────────────────

def entry_link(request, pk):
    entry = get_object_or_404(Entry, pk=pk)
    if request.method == "POST":
        form = EntryLinkForm(request.POST, exclude_entry=entry)
        if form.is_valid():
            link = form.save(commit=False)
            link.from_entry = entry
            link.save()
            messages.success(request, "Link created.")
            return redirect("core:entry_detail", pk=pk)
    else:
        form = EntryLinkForm(exclude_entry=entry)
    return render(request, "core/entry_link.html", {"form": form, "entry": entry})


def link_delete(request, link_pk):
    link = get_object_or_404(EntryLink, pk=link_pk)
    from_pk = link.from_entry_id
    if request.method == "POST":
        link.delete()
        messages.success(request, "Link removed.")
        return redirect("core:entry_detail", pk=from_pk)
    return render(request, "core/confirm_delete.html", {"object": link, "type": "link"})


# ── Reports ────────────────────────────────────────────────────────────────────

class ReportListView(ListView):
    model = Report
    template_name = "core/report_list.html"
    context_object_name = "reports"
    paginate_by = 20


class ReportDetailView(DetailView):
    model = Report
    template_name = "core/report_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["content_html"] = md_lib.markdown(
            self.object.content, extensions=["fenced_code", "tables", "toc"]
        )
        return ctx


def report_create(request):
    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            topic = form.cleaned_data["topic"]
            title = form.cleaned_data["title"]
            provider = form.cleaned_data["llm_provider"]
            selection = form.cleaned_data["entry_selection"]

            if selection == "topic":
                q = Q(title__icontains=topic) | Q(tags__name__icontains=topic) | Q(content__icontains=topic)
                entries = list(Entry.objects.filter(q).distinct()[:40])
            elif selection == "all":
                entries = list(Entry.objects.all()[:40])
            else:
                entries = list(form.cleaned_data["selected_entries"])

            if not entries:
                messages.warning(request, "No entries matched the topic. Try 'All entries' or select manually.")
                return render(request, "core/report_form.html", {"form": form})

            try:
                from agents.report_generator import generate_report
                content = generate_report(topic=topic, entries=entries, provider=provider)
            except Exception as exc:
                messages.error(request, f"Report generation failed: {exc}")
                return render(request, "core/report_form.html", {"form": form})

            report = Report.objects.create(
                title=title,
                topic=topic,
                content=content,
                llm_provider=provider,
            )
            report.entries.set(entries)

            from utils.md_writer import write_report_md
            report.md_filepath = str(write_report_md(report))
            report.save(update_fields=["md_filepath"])

            messages.success(request, f"Report '{title}' generated.")
            return redirect("core:report_detail", pk=report.pk)

    else:
        form = ReportForm()

    return render(request, "core/report_form.html", {"form": form})


def report_delete(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if request.method == "POST":
        title = report.title
        report.delete()
        messages.success(request, f"Report '{title}' deleted.")
        return redirect("core:report_list")
    return render(request, "core/confirm_delete.html", {"object": report, "type": "report"})


# ── Chat ───────────────────────────────────────────────────────────────────────

def chat_list(request):
    sessions = ChatSession.objects.annotate(msg_count=Count("messages")).order_by("-updated_at")
    return render(request, "core/chat_list.html", {"sessions": sessions})


def chat_new(request):
    prefill_title = ""
    prefill_note = ""
    entry_pk = request.GET.get("entry_pk")
    if entry_pk:
        try:
            entry = Entry.objects.get(pk=entry_pk)
            prefill_title = f"Chat about: {entry.title}"
            prefill_note = entry.title
        except Entry.DoesNotExist:
            pass

    if request.method == "POST":
        form = ChatSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            return redirect("core:chat_session", pk=session.pk)
    else:
        form = ChatSessionForm(initial={"title": prefill_title})

    return render(request, "core/chat_new.html", {"form": form, "prefill_note": prefill_note})


def chat_session(request, pk):
    session = get_object_or_404(ChatSession, pk=pk)
    msgs = session.messages.prefetch_related("cited_entries__category").order_by("created_at")
    return render(request, "core/chat_session.html", {
        "session": session,
        "messages": msgs,
    })


@require_POST
def chat_message(request, pk):
    session = get_object_or_404(ChatSession, pk=pk)
    try:
        body = json.loads(request.body)
        user_message = body.get("message", "").strip()
    except (json.JSONDecodeError, AttributeError):
        user_message = request.POST.get("message", "").strip()

    if not user_message:
        return JsonResponse({"error": "Empty message."}, status=400)

    try:
        from agents.chat_agent import chat
        result = chat(session_id=session.pk, user_message=user_message)
        return JsonResponse(result)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


def apply_edit_suggestion(request, msg_pk, entry_pk):
    message = get_object_or_404(ChatMessage, pk=msg_pk)
    entry = get_object_or_404(Entry, pk=entry_pk)

    # Parse the edit block for this entry out of the message
    import re
    pattern = re.compile(rf"\[EDIT:{entry_pk}\](.*?)\[/EDIT\]", re.DOTALL)
    match = pattern.search(message.content)
    proposed = match.group(1).strip() if match else ""

    form = EntryConfirmForm(instance=entry, initial={
        "content": proposed,
        "tags_input": entry.tag_list(),
    })
    return render(request, "core/entry_add.html", {
        "step": "2",
        "confirm_form": form,
        "edit_mode": True,
        "entry": entry,
        "tags_prefill": entry.tag_list(),
        "edit_source_note": f"AI suggestion from chat session: {message.session.title}",
    })


def chat_delete(request, pk):
    session = get_object_or_404(ChatSession, pk=pk)
    if request.method == "POST":
        title = session.title
        session.delete()
        messages.success(request, f"Chat session '{title}' deleted.")
        return redirect("core:chat_list")
    return render(request, "core/confirm_delete.html", {"object": session, "type": "chat session"})


# ── Graph ──────────────────────────────────────────────────────────────────────

# Bootstrap color name → hex (matches config.py color values)
_COLOR_MAP = {
    "primary":   "#0d6efd",
    "success":   "#198754",
    "warning":   "#ffc107",
    "secondary": "#6c757d",
    "info":      "#0dcaf0",
    "danger":    "#dc3545",
    "dark":      "#212529",
}

_RELATIONSHIP_COLORS = {
    "supports":    "#198754",
    "contradicts": "#dc3545",
    "extends":     "#0d6efd",
    "cites":       "#6c757d",
    "uses":        "#6f42c1",
    "challenges":  "#fd7e14",
}


def graph_view(request):
    return render(request, "core/graph.html")


def graph_data(request):
    entries = (
        Entry.objects
        .select_related("category")
        .prefetch_related("tags")
        .annotate(link_count=Count("outgoing_links"))
    )
    links = EntryLink.objects.select_related("from_entry", "to_entry").all()

    nodes = [
        {
            "id": e.pk,
            "title": e.title,
            "category": e.category.slug,
            "category_label": e.category.name,
            "color": _COLOR_MAP.get(e.category.color, "#6c757d"),
            "icon": e.category.icon,
            "word_count": e.word_count(),
            "url": e.get_absolute_url(),
            "tags": [t.name for t in e.tags.all()],
            "link_count": e.link_count,
            "source": e.source,
        }
        for e in entries
    ]

    edges = [
        {
            "source": lk.from_entry_id,
            "target": lk.to_entry_id,
            "relationship": lk.relationship,
            "label": lk.get_relationship_display(),
            "note": lk.note,
            "color": _RELATIONSHIP_COLORS.get(lk.relationship, "#999"),
        }
        for lk in links
    ]

    categories = [
        {"slug": c.slug, "name": c.name, "icon": c.icon, "color": _COLOR_MAP.get(c.color, "#6c757d")}
        for c in Category.objects.order_by("name")
    ]

    return JsonResponse({"nodes": nodes, "links": edges, "categories": categories})
