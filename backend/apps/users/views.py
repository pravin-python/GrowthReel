"""Views for the Django-rendered login/logout flow.

`CustomLoginView` is step 1-2 of the bridge: a normal Django session login
(POST to `/accounts/login/`), and on success, instead of redirecting to a
Django page, the browser is redirected to
`APP_FRONTEND_URL/auth/callback?token=<bridge_jwt>` so the React SPA at
app.growthreel.com can hand that token to the FastAPI service.
"""
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView

from apps.users.services import issue_bridge_token


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        # Login responses (and anything in this flow that could carry the
        # bridge JWT) must never be cached by the browser or a proxy.
        request._growthreel_no_store = True
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self) -> str:
        token = issue_bridge_token(self.request.user)
        query = urlencode({"token": token})
        return f"{settings.APP_FRONTEND_URL}/auth/callback?{query}"


class CustomLogoutView(LogoutView):
    next_page = "home"

    def dispatch(self, request, *args, **kwargs):
        request._growthreel_no_store = True
        return super().dispatch(request, *args, **kwargs)
