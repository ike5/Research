from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default="📄")
    color = models.CharField(max_length=20, default="secondary")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Entry(models.Model):
    title = models.CharField(max_length=300)
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="entries")
    source = models.CharField(max_length=500, blank=True, help_text="Author, institution, or citation")
    source_url = models.URLField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    linked_entries = models.ManyToManyField(
        "self",
        through="EntryLink",
        symmetrical=False,
        related_name="linked_from",
        blank=True,
    )
    classification_reasoning = models.TextField(blank=True)
    confidence = models.CharField(max_length=20, blank=True)
    llm_provider = models.CharField(max_length=50, blank=True)
    md_filepath = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "entries"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:entry_detail", args=[self.pk])

    def word_count(self):
        return len(self.content.split())

    def tag_list(self):
        return ", ".join(t.name for t in self.tags.all())


class EntryLink(models.Model):
    RELATIONSHIP_CHOICES = [
        ("supports", "Supports"),
        ("contradicts", "Contradicts"),
        ("extends", "Extends"),
        ("cites", "Cites"),
        ("uses", "Uses methodology from"),
        ("challenges", "Challenges"),
    ]

    from_entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="outgoing_links")
    to_entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="incoming_links")
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("from_entry", "to_entry")]
        ordering = ["relationship"]

    def __str__(self):
        return f"{self.from_entry.title} → {self.get_relationship_display()} → {self.to_entry.title}"


class Report(models.Model):
    title = models.CharField(max_length=300)
    topic = models.CharField(max_length=300)
    content = models.TextField()
    entries = models.ManyToManyField(Entry, blank=True, related_name="reports")
    llm_provider = models.CharField(max_length=50, blank=True)
    md_filepath = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:report_detail", args=[self.pk])


class ChatSession(models.Model):
    MODE_CHOICES = [
        ("explore", "Explore — ask questions"),
        ("contest", "Contest — challenge & stress-test"),
        ("edit",    "Edit — suggest revisions"),
    ]

    title = models.CharField(max_length=300)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="explore")
    llm_provider = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:chat_session", args=[self.pk])

    def message_count(self):
        return self.messages.count()


class ChatMessage(models.Model):
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    cited_entries = models.ManyToManyField(Entry, blank=True, related_name="chat_citations")
    has_edit_suggestion = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
