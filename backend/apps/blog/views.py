from django.views.generic import DetailView, ListView

from apps.blog.selectors import get_post_by_slug, get_published_posts


class PostListView(ListView):
    template_name = "blog/list.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        return get_published_posts()


class PostDetailView(DetailView):
    template_name = "blog/detail.html"
    context_object_name = "post"

    def get_object(self, queryset=None):
        return get_post_by_slug(self.kwargs["slug"])
