from django.contrib import admin
from django.utils.html import format_html
import os

from .models import (
    Category,
    Retailer,
    Discount,
    SharedDiscount,
    Conversation,
    ConversationMessage,
    SearchRequest,
    UserPreference,
    ConversationContext,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "image_preview",
        "created_at",
        "updated_at",
    )
    search_fields = ("name",)
    list_filter = ("created_at", "updated_at")
    ordering = ("created_at",)
    date_hierarchy = "created_at"

    def image_preview(self, obj: Category) -> str:
        if obj.image:
            ext = os.path.splitext(obj.image.url)[-1].lower()
            if ext == ".svg":
                return format_html(
                    '<object data="{}" type="image/svg+xml" width="50" height="50"></object>',
                    obj.image.url,
                )
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:5px;" />',
                obj.image.url,
            )
        return "No Image"

    image_preview.short_description = "Preview"


@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "contact_info",
        "location",
        "owner",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "contact_info", "owner__username")
    list_filter = ("created_at", "updated_at")
    ordering = ("created_at",)
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(None)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "retailer",
        "category",
        "description_preview",
        "discount_code",
        "discount_value",
        "is_active",
        "expiration_date",
        "image_preview",
        "created_at",
    )
    list_filter = (
        "category",
        "is_active",
        "expiration_date",
        "created_at",
    )
    search_fields = (
        "retailer__name",
        "description",
        "discount_code",
        "country",
        "brand",
    )
    ordering = ("-created_at",)
    date_hierarchy = "expiration_date"

    def description_preview(self, obj: Discount) -> str:
        if obj.description:
            return obj.description[:50] + ("..." if len(obj.description) > 50 else "")
        return ""
    description_preview.short_description = "Description"

    def image_preview(self, obj: Discount) -> str:
        if obj.image:
            ext = os.path.splitext(obj.image.url)[-1].lower()
            if ext == ".svg":
                return format_html(
                    '<object data="{}" type="image/svg+xml" width="50" height="50"></object>',
                    obj.image.url,
                )
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:5px;" />',
                obj.image.url,
            )
        return "No Image"
    image_preview.short_description = "Preview"


@admin.register(SharedDiscount)
class SharedDiscountAdmin(admin.ModelAdmin):
    list_display = (
        "discount",
        "group_name",
        "participant_count",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = (
        "group_name",
        "discount__discount_code",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("participants",)

    def participant_count(self, obj: SharedDiscount) -> int:
        return len(obj.participants or [])
    participant_count.short_description = "Participants"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "status",
        "message_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("title", "user__username")
    ordering = ("-updated_at",)
    date_hierarchy = "updated_at"


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "role",
        "message_type",
        "content",
        "created_at",
    )
    list_filter = ("role", "message_type", "created_at")
    search_fields = ("content", "conversation__id", "conversation__user__username")
    ordering = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(SearchRequest)
class SearchRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "query",
        "status",
        "result_count",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "created_at", "completed_at")
    search_fields = ("query", "conversation__user__username")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "preference_type",
        "key",
        "value",
        "confidence",
        "created_at",
    )
    list_filter = ("preference_type", "created_at")
    search_fields = ("key", "value", "user__username")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


@admin.register(ConversationContext)
class ConversationContextAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "stage",
        "user_intent",
        "successful_searches",
        "failed_searches",
        "updated_at",
    )
    list_filter = ("stage", "updated_at")
    search_fields = ("conversation__id",)
    ordering = ("-updated_at",)
    date_hierarchy = "updated_at"