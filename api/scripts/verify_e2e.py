"""Throwaway verification script (not part of the shipped app). Uses this
project's own venv (with django.setup() access to the same DB as the real
backend) to mint a genuine bridge token exactly as the real Django login
view would, then prints it so the shell can POST it to the running dev
server. Also ensures a Lead and a Post exist to exercise those endpoints.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.django_orm import setup_django  # noqa: E402

setup_django()

from apps.blog.models import Post  # noqa: E402
from apps.crm.models import Lead  # noqa: E402
from apps.users.models import User  # noqa: E402
from apps.users.services import issue_bridge_token  # noqa: E402

user = User.objects.first()
if user is None:
    user = User.objects.create_user(email="verify@growthreel.com", password="not-used-here")
    print(f"created user {user.email}", file=sys.stderr)
else:
    print(f"using existing user {user.email}", file=sys.stderr)

lead = Lead.objects.first()
if lead is None:
    lead = Lead.objects.create(name="Verify Lead", email="lead@example.com", source="e2e-script")
    print(f"created lead id={lead.pk}", file=sys.stderr)
else:
    print(f"using existing lead id={lead.pk} status={lead.status}", file=sys.stderr)

post = Post.objects.first()
if post is None:
    post = Post.objects.create(
        title="Verify Post", body="body text", author=user, status=Post.Status.PUBLISHED
    )
    print(f"created post id={post.pk}", file=sys.stderr)
else:
    print(f"using existing post id={post.pk}", file=sys.stderr)

bridge_token = issue_bridge_token(user)
print(bridge_token)
print(f"LEAD_ID={lead.pk}", file=sys.stderr)
