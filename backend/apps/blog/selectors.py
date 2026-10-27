"""Read-only queries for the blog app."""
from __future__ import annotations

from django.db.models import QuerySet
from django.http import Http404

from apps.blog.models import Post


def get_published_posts() -> QuerySet[Post]:
    return Post.objects.filter(status=Post.Status.PUBLISHED).select_related("author", "category")


def get_post_by_slug(slug: str) -> Post:
    """Returns the published post with this slug, or raises Http404.

    Anonymous/public visitors should never be able to discover an
    unpublished post by guessing its slug.
    """
    post = (
        Post.objects.filter(slug=slug, status=Post.Status.PUBLISHED)
        .select_related("author", "category")
        .first()
    )
    if post is None:
        raise Http404("Post not found")
    return post
