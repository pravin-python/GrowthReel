from django.contrib import admin

from apps.blog.models import Category, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "status", "published_at", "created_at"]
    list_filter = ["status", "category"]
    search_fields = ["title", "excerpt", "body", "tags"]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["author", "category"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        # Admins need to see soft-deleted posts too.
        return Post.all_objects.select_related("author", "category")
