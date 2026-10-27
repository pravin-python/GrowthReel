"""Business logic for the blog app. These are the only functions that may
mutate a Post (the Django admin routes through these too, via ModelAdmin
save_model overrides — see admin.py).
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.blog.models import Post


def create_post(*, author, title: str, body: str, **extra_fields: Any) -> Post:
    post = Post(author=author, title=title, body=body, **extra_fields)
    post.save()
    return post


def update_post(post: Post, **fields: Any) -> Post:
    for field, value in fields.items():
        setattr(post, field, value)
    post.save()
    return post


def publish_post(post: Post) -> Post:
    """Marks a post published and stamps `published_at` if not already set."""
    post.status = Post.Status.PUBLISHED
    if post.published_at is None:
        post.published_at = timezone.now()
    post.save(update_fields=["status", "published_at", "updated_at"])
    return post


def unpublish_post(post: Post) -> Post:
    post.status = Post.Status.DRAFT
    post.save(update_fields=["status", "updated_at"])
    return post
