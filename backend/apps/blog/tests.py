"""Tests for the blog app: the services/selectors split and the public views."""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.blog.models import Post
from apps.blog.selectors import get_post_by_slug, get_published_posts
from apps.blog.services import create_post, publish_post, unpublish_post
from apps.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def author():
    return User.objects.create_user(email="author@example.com", password="s3cret-pass")


def test_create_post_defaults_to_draft_with_generated_slug(author):
    post = create_post(author=author, title="Hello, GrowthReel", body="Body text.")

    assert post.status == Post.Status.DRAFT
    assert post.slug == "hello-growthreel"


def test_publish_post_stamps_published_at_once(author):
    post = create_post(author=author, title="Launch day", body="Body text.")

    published = publish_post(post)
    first_published_at = published.published_at
    assert published.status == Post.Status.PUBLISHED
    assert first_published_at is not None

    # Re-publishing an already-published post must not move the timestamp.
    publish_post(post)
    post.refresh_from_db()
    assert post.published_at == first_published_at


def test_unpublish_post_reverts_to_draft(author):
    post = create_post(author=author, title="Oops", body="Body text.")
    publish_post(post)

    unpublish_post(post)
    post.refresh_from_db()
    assert post.status == Post.Status.DRAFT


def test_get_published_posts_excludes_drafts(author):
    draft = create_post(author=author, title="Draft post", body="...")
    published = create_post(author=author, title="Published post", body="...")
    publish_post(published)

    slugs = set(get_published_posts().values_list("slug", flat=True))
    assert published.slug in slugs
    assert draft.slug not in slugs


def test_get_post_by_slug_404s_for_unpublished(author):
    from django.http import Http404

    draft = create_post(author=author, title="Secret draft", body="...")

    with pytest.raises(Http404):
        get_post_by_slug(draft.slug)


def test_blog_list_view_returns_200(client):
    response = client.get(reverse("blog:list"))
    assert response.status_code == 200


def test_blog_detail_view_404s_for_unknown_slug(client):
    response = client.get(reverse("blog:detail", kwargs={"slug": "does-not-exist"}))
    assert response.status_code == 404


def test_blog_detail_view_200s_for_published_post(client, author):
    post = create_post(author=author, title="Visible post", body="...")
    publish_post(post)

    response = client.get(reverse("blog:detail", kwargs={"slug": post.slug}))
    assert response.status_code == 200
