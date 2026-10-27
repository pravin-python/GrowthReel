"""Blog models. Mutation is restricted to `apps.blog.services` — see there."""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import SoftDeleteModel, TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # Slug derivation from name is data normalization intrinsic to the
        # model (equivalent to `auto_now`), not business logic, so it stays
        # here rather than in services.py.
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    excerpt = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    cover_image = models.ImageField(upload_to="blog/covers/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="posts"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )
    # Simple comma-separated tag list, per the spec ("tags (M2M via through
    # or simple CharField list is fine").
    tags = models.CharField(
        max_length=255, blank=True, help_text="Comma-separated tags, e.g. 'django,api'"
    )

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        # Same rationale as Category.save(): slug-from-title is intrinsic
        # data normalization, not domain business logic.
        if not self.slug:
            self.slug = slugify(self.title)[:280]
        super().save(*args, **kwargs)

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED
