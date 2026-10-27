from django.contrib import admin

from apps.crm.models import Client, Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    """This is the CRM page: the user manages leads from the Django admin."""

    list_display = ["name", "email", "company", "status", "source", "owner", "created_at"]
    list_filter = ["status", "source"]
    search_fields = ["name", "email", "company", "phone"]
    autocomplete_fields = ["owner"]
    readonly_fields = ["created_at", "updated_at"]
    list_select_related = ["owner"]

    def get_queryset(self, request):
        return Lead.all_objects.select_related("owner")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_email", "contact_phone", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "contact_email"]
