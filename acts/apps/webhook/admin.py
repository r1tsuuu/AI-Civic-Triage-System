from django.contrib import admin
from .models import RawPost


@admin.register(RawPost)
class RawPostAdmin(admin.ModelAdmin):
    list_display = ("facebook_post_id", "received_at", "processed")
    list_filter = ("processed",)
    search_fields = ("facebook_post_id", "post_text")
    readonly_fields = ("id", "received_at")
    ordering = ("-received_at",)