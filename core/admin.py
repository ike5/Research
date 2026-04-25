from django.contrib import admin
from .models import Category, Tag, Entry, EntryLink, Report, ChatSession, ChatMessage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["icon", "name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class EntryLinkInline(admin.TabularInline):
    model = EntryLink
    fk_name = "from_entry"
    extra = 0


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "llm_provider", "confidence", "created_at"]
    list_filter = ["category", "llm_provider", "tags"]
    search_fields = ["title", "content", "source"]
    filter_horizontal = ["tags"]
    inlines = [EntryLinkInline]
    readonly_fields = ["created_at", "updated_at", "md_filepath"]


@admin.register(EntryLink)
class EntryLinkAdmin(admin.ModelAdmin):
    list_display = ["from_entry", "relationship", "to_entry"]
    list_filter = ["relationship"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["title", "topic", "llm_provider", "created_at"]
    filter_horizontal = ["entries"]
    readonly_fields = ["created_at", "md_filepath"]


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ["role", "content", "created_at"]


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["title", "mode", "llm_provider", "created_at"]
    list_filter = ["mode"]
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["session", "role", "has_edit_suggestion", "created_at"]
    list_filter = ["role", "has_edit_suggestion"]
    readonly_fields = ["created_at"]
