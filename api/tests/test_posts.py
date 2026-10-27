import pytest


@pytest.fixture()
def post(django_user):
    from apps.blog.services import create_post

    return create_post(author=django_user, title="Hello, GrowthReel", body="Body text.")


def test_list_posts_requires_auth(client):
    response = client.get("/api/v1/posts")

    assert response.status_code == 401


def test_list_posts_includes_drafts(client, auth_headers, post, django_user):
    # This is the internal/admin content screen, so unlike the public Django
    # blog it must show drafts too, not just published posts.
    response = client.get("/api/v1/posts", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    match = next(item for item in body if item["id"] == str(post.pk))
    assert match["status"] == "draft"
    assert match["author_email"] == django_user.email
    assert match["published_at"] is None
