"""Posts endpoint. This is the internal/admin view (all posts, any status),
not the public-only selector (`apps.blog.selectors.get_published_posts`)
that the Django-rendered public blog uses.
"""
from __future__ import annotations

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import PostOut

router = APIRouter()


def _list_posts_sync() -> list:
    from apps.blog.models import Post

    return list(Post.objects.select_related("author").all())


@router.get("/posts", response_model=list[PostOut])
async def list_posts(user=Depends(get_current_user)) -> list[PostOut]:
    posts = await sync_to_async(_list_posts_sync)()
    return [
        PostOut(
            id=str(post.pk),
            title=post.title,
            slug=post.slug,
            status=post.status,
            published_at=post.published_at,
            author_email=post.author.email,
        )
        for post in posts
    ]
