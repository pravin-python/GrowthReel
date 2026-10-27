from django.urls import path

from apps.users.views import CustomLoginView, CustomLogoutView

app_name = "users"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
]
