from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Retailer, Discount, SharedDiscount


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the Category model.
    """
    list_display: tuple[str, str, str, str] = ("name", "image_preview", "created_at", "updated_at")
    search_fields: tuple[str] = ("name",)
    ordering: tuple[str] = ("created_at",)

    def image_preview(self, obj: Category) -> str:
        """
        Displays a preview of the category image in the admin panel.

        Args:
            obj (Category): The category object whose image should be previewed.

        Returns:
            str: An HTML formatted image tag or a message indicating no image is available.
        """
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:5px;" />', obj.image.url)
        return "No Image"

    image_preview.short_description = "Preview"


@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the Retailer model.
    """
    list_display: tuple[str, str, str, str, str] = ("name", "contact_info", "location", "created_at", "updated_at")
    search_fields: tuple[str] = ("name", "contact_info")
    ordering: tuple[str] = ("created_at",)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the Discount model.
    """
    list_display: tuple[str, str, str, str, str, str, str, str] = (
        "retailer", "category", "description_preview", "discount_code", "expiration_date", "image_preview", "created_at", "updated_at"
    )
    list_filter: tuple[str] = ("category", "expiration_date")
    search_fields: tuple[str] = ("retailer__name", "description", "discount_code")
    ordering: tuple[str] = ("-created_at",)

    def description_preview(self, obj: Discount) -> str:
        """
        Displays a shortened preview of the discount description.

        Args:
            obj (Discount): The discount object whose description is to be previewed.

        Returns:
            str: A shortened version of the discount description.
        """
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description

    description_preview.short_description = "Description"

    def image_preview(self, obj: Discount) -> str:
        """
        Displays a preview of the discount image in the admin panel.

        Args:
            obj (Discount): The discount object whose image should be previewed.

        Returns:
            str: An HTML formatted image tag or a message indicating no image is available.
        """
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:5px;" />', obj.image.url)
        return "No Image"

    image_preview.short_description = "Preview"


@admin.register(SharedDiscount)
class SharedDiscountAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the SharedDiscount model.
    """
    list_display: tuple[str, str, str, str, str] = ("discount", "group_name", "status", "created_at", "updated_at")
    list_filter: tuple[str] = ("status",)
    search_fields: tuple[str] = ("group_name", "discount__discount_code")
    ordering: tuple[str] = ("-created_at",)
