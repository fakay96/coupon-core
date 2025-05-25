"""
Discount Discovery System – Models
==================================

A geospatial, S3-backed platform where retailers publish location-aware
discounts and users can share group codes.  All user records live in a **separate
database shard**, so every FK to the user model disables the database-level
constraint with ``db_constraint=False``.

Main entities
-------------
* **Category**         – Thematic bucket (Pizza, Shoes…) with an S3 image.
* **Retailer**         – Business with a geo-point and optional owner account.
* **Discount**         – Single offer; supports semantic-search embeddings.
* **SharedDiscount**   – Group-purchase wrapper around a Discount.
* **Conversation …**   – Chat/logging layer that extracts user preferences.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from storages.backends.s3boto3 import S3Boto3Storage

from coupon_core.utils.logging import geo_logger, geo_structured_logger


# --------------------------------------------------------------------------- #
#  Category                                                                   #
# --------------------------------------------------------------------------- #
class Category(models.Model):
    """
    A thematic bucket used to group discounts (e.g. *Pizza*, *Shoes*).

    An optional image is uploaded to DigitalOcean Spaces via ``django-storages``.
    """

    name = models.CharField(
        max_length=255, unique=True, help_text="Human-friendly category name."
    )
    image = models.FileField(
        upload_to="categories/",
        storage=S3Boto3Storage(),
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "svg"])],
        null=True,
        blank=True,
        help_text="Optional SVG/PNG/JPEG stored in Spaces.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        ordering = ["name"]

    # --------------------------------------------------------------------- #
    def __str__(self) -> str:  # pragma: no cover
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Wrap default save in structured logging."""
        try:
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "Category saved",
                "category_save",
                {"category_id": self.id, "name": self.name},
            )
        except Exception as exc:  # pragma: no cover
            geo_structured_logger.error(
                geo_logger,
                "Error saving category",
                "category_save",
                exc,
                {"name": self.name},
            )
            raise


# --------------------------------------------------------------------------- #
#  Retailer                                                                   #
# --------------------------------------------------------------------------- #
class Retailer(models.Model):
    """
    A business that can attach one or more :class:`Discount` objects.

    The ``location`` field is a :class:`PointField`` so geo-searches run on PostGIS.
    """

    name = models.CharField(
        max_length=255, unique=True, help_text="Public-facing retailer name."
    )
    contact_info = models.TextField(
        null=True, blank=True, help_text="Address / phone / email."
    )
    location = gis_models.PointField(
        help_text="WGS-84 lon/lat of the store HQ or flagship.",
        null=True,
        blank=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
        db_constraint=False,  # user lives on another DB
        help_text="Account that manages this retailer.",
    )
    analytics_data: Dict[str, Any] = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary stats (sales, clicks…) collected downstream.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retailers"
        ordering = ["name"]

    # --------------------------------------------------------------------- #
    def __str__(self) -> str:  # pragma: no cover
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        try:
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "Retailer saved",
                "retailer_save",
                {"retailer_id": self.id, "name": self.name, "owner_id": self.owner_id},
            )
        except Exception as exc:  # pragma: no cover
            geo_structured_logger.error(
                geo_logger,
                "Error saving retailer",
                "retailer_save",
                exc,
                {"name": self.name, "owner_id": self.owner_id},
            )
            raise


# --------------------------------------------------------------------------- #
#  Discount                                                                   #
# --------------------------------------------------------------------------- #
class Discount(models.Model):
    """
    A single price promotion, optionally tied to a geo-fence.

    Vector embeddings (``embedding``) let us rank results semantically.
    """


    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.CASCADE,
        related_name="discounts",
        help_text="Publisher of the discount.",
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="discounts",
        help_text="Optional thematic category.",
    )

    description = models.TextField(null=True, blank=True)
    discount_code = models.CharField(max_length=50, unique=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_active = models.BooleanField(default=True)
    expiration_date = models.DateTimeField()

    location = gis_models.PointField(
        null=True, blank=True, help_text="Where the offer can be redeemed."
    )
    image = models.FileField(
        upload_to="discounts/",
        storage=S3Boto3Storage(),
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "svg"])],
        null=True,
        blank=True,
    )

    # --- Optional commerce metadata --- #
    currency = models.CharField(max_length=3, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    brand = models.CharField(max_length=255, null=True, blank=True)

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    validity_dates = models.CharField(max_length=255, null=True, blank=True)

    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)

    # --- Source provenance --- #
    source = models.CharField(max_length=255, null=True, blank=True)
    source_id = models.CharField(max_length=255, null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)

    # --- Product / store refs --- #
    product_id = models.CharField(max_length=255, null=True, blank=True)
    product_url = models.URLField(null=True, blank=True)
    store_name = models.CharField(max_length=255, null=True, blank=True)
    store_id = models.CharField(max_length=255, null=True, blank=True)
    store_url = models.URLField(null=True, blank=True)

    price_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    stock_info = models.TextField(null=True, blank=True)

    # --- ML search bits --- #
    embedding = ArrayField(
        base_field=models.FloatField(), size=768, null=True, blank=True
    )

    # --- Misc --- #
    error_message = models.TextField(null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    size = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "discounts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "expiration_date"]),
            models.Index(fields=["location"]),
        ]

    # --------------------------------------------------------------------- #
    def __str__(self) -> str:  # pragma: no cover
        return f"{self.retailer.name} — {self.discount_code}"

    # --------------------------------------------------------------------- #
    # Validation & save guards                                              #
    # --------------------------------------------------------------------- #
    def clean(self) -> None:
        """Ensure ``expiration_date`` is in the future."""
        if self.expiration_date is None:
            # No expiry provided → skip this check (or raise your own error if you prefer)
            return
        if self.expiration_date <= timezone.now():
            geo_structured_logger.warning(
                geo_logger,
                "Past expiry",
                "discount_clean",
                {"discount_id": self.id, "expiry": self.expiration_date.isoformat()},
            )
            raise ValidationError(_("Expiration date must be in the future."))

    def save(self, *args: Any, **kwargs: Any) -> None:
        try:
            self.full_clean()
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "Discount saved",
                "discount_save",
                {
                    "discount_id": self.id,
                    "retailer_id": self.retailer_id,
                    "category_id": self.category_id,
                },
            )
        except ValidationError as ve:  # pragma: no cover
            geo_structured_logger.error(
                geo_logger,
                "Validation error",
                "discount_save",
                ve,
                {"retailer_id": self.retailer_id},
            )
            raise
        except Exception as exc:  # pragma: no cover
            geo_structured_logger.error(
                geo_logger,
                "Unexpected error",
                "discount_save",
                exc,
                {"retailer_id": self.retailer_id},
            )
            raise



class SharedDiscount(models.Model):
    """A simple group-purchase / referral wrapper around :class:`Discount`."""

    discount = models.ForeignKey(
        Discount,
        on_delete=models.CASCADE,
        related_name="shared_discounts",
        help_text="Underlying discount being shared.",
    )
    group_name = models.CharField(max_length=255)
    participants: List[int] = models.JSONField(
        help_text="User IDs of participants.",
    )
    min_participants = models.PositiveIntegerField(default=2)
    max_participants = models.PositiveIntegerField(default=10)
    status = models.CharField(
        max_length=50,
        choices=[("active", "Active"), ("completed", "Completed"), ("expired", "Expired")],
        default="active",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shared_discounts"
        ordering = ["-created_at"]

    # --------------------------------------------------------------------- #
    def __str__(self) -> str:  # pragma: no cover
        return f"{self.group_name} — {self.discount.discount_code}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        try:
            super().save(*args, **kwargs)
            geo_structured_logger.info(
                geo_logger,
                "Shared discount saved",
                "shared_discount_save",
                {
                    "shared_discount_id": self.id,
                    "discount_id": self.discount_id,
                    "status": self.status,
                },
            )
        except Exception as exc:  # pragma: no cover
            geo_structured_logger.error(
                geo_logger,
                "Error saving shared discount",
                "shared_discount_save",
                exc,
                {"discount_id": self.discount_id},
            )
            raise


# --------------------------------------------------------------------------- #
#  Conversation-related models                                                #
# --------------------------------------------------------------------------- #
class Conversation(models.Model):
    """A single chat session between *one* user and the assistant."""

    class ConversationStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_constraint=False,  # cross-shard FK
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Auto-generated from the first user turn.",
    )
    status = models.CharField(
        max_length=20, choices=ConversationStatus.choices, default=ConversationStatus.ACTIVE
    )

    user_preferences = models.JSONField(
        default=dict, blank=True, help_text="Lightweight prefs extracted in-chat."
    )
    last_location = gis_models.PointField(
        null=True, blank=True, help_text="Last lat/lon supplied by the user."
    )
    last_radius = models.FloatField(
        default=5_000.0, help_text="Search radius (m) to assume when geo-filtering."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["status"]),
        ]

    # --------------------------------------------------------------------- #
    def __str__(self) -> str:  # pragma: no cover
        return f"Conversation {self.id} — {getattr(self.user, 'username', 'unknown')}"

    @property
    def message_count(self) -> int:
        return self.messages.count()

    @property
    def last_message(self) -> "ConversationMessage | None":
        return self.messages.order_by("-created_at").first()

    # Helper to set the sidebar title ------------------------------------- #
    def generate_title(self) -> None:
        first = self.messages.filter(role=ConversationMessage.MessageRole.USER).first()
        if first:
            preview = first.content[:50]
            self.title = f"{preview}…" if len(first.content) > 50 else preview
            self.save(update_fields=["title"])


# --------------------------------------------------------------------------- #
class ConversationMessage(models.Model):
    """A single utterance (user / assistant / system)."""

    class MessageRole(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    class MessageType(models.TextChoices):
        GREETING = "greeting", "Greeting"
        SEARCH_QUERY = "search_query", "Search Query"
        SEARCH_RESULTS = "search_results", "Search Results"
        CONVERSATION = "conversation", "Conversation"
        ERROR = "error", "Error"
        SYSTEM_INFO = "system_info", "System Info"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    message_type = models.CharField(
        max_length=20, choices=MessageType.choices, default=MessageType.CONVERSATION
    )
    content = models.TextField()

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary structured data (token count, model name…).",
    )
    search_request = models.ForeignKey(
        "SearchRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Link if this message produced a search.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "conversation_messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["role", "message_type"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.role}: {self.content[:50]}…"


# --------------------------------------------------------------------------- #
class SearchRequest(models.Model):
    """
    A geo-aware product/location search triggered during a conversation.
    """

    class SearchStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        TIMEOUT = "timeout", "Timeout"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="search_requests"
    )

    query = models.TextField(help_text="Raw user query.")
    location = gis_models.PointField(help_text="Lon/lat used as search centre.")
    radius = models.FloatField(default=5_000.0, help_text="Radius in metres.")
    search_context = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20, choices=SearchStatus.choices, default=SearchStatus.PENDING
    )
    results = models.JSONField(default=list, blank=True)
    result_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processing_time = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "search_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Search «{self.query[:50]}…» ({self.status})"

    # Convenience helpers -------------------------------------------------- #
    def mark_completed(self, *, results: List[Dict], processing_time: float | None = None) -> None:
        from django.utils import timezone

        self.status = self.SearchStatus.COMPLETED
        self.results = results
        self.result_count = len(results)
        self.completed_at = timezone.now()
        if processing_time is not None:
            self.processing_time = processing_time
        self.save(
            update_fields=[
                "status",
                "results",
                "result_count",
                "completed_at",
                "processing_time",
            ]
        )

    def mark_failed(self, *, error_message: str = "") -> None:
        from django.utils import timezone

        self.status = self.SearchStatus.FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])


# --------------------------------------------------------------------------- #
class UserPreference(models.Model):
    """
    A single preference pattern extracted from any conversation a user has.
    """

    class PreferenceType(models.TextChoices):
        CATEGORY = "category", "Category"
        LOCATION = "location", "Location"
        PRICE_RANGE = "price_range", "Price Range"
        BRAND = "brand", "Brand"
        SEARCH_RADIUS = "search_radius", "Search Radius"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
        db_constraint=False,  # cross-shard FK
    )
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="extracted_preferences"
    )

    preference_type = models.CharField(max_length=20, choices=PreferenceType.choices)
    key = models.CharField(max_length=100, help_text="Canonical preference key.")
    value = models.TextField(help_text="Raw value (plain or JSON string).")
    confidence = models.FloatField(
        default=0.5, help_text="0–1 confidence score from the extractor."
    )

    extracted_from_message = models.ForeignKey(
        ConversationMessage, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_preferences"
        unique_together = ["user", "preference_type", "key"]
        indexes = [
            models.Index(fields=["user", "preference_type"]),
            models.Index(fields=["confidence"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_id} • {self.key} → {self.value}"


# --------------------------------------------------------------------------- #
class ConversationContext(models.Model):
    """
    Cached summary of the latest state of a conversation.

    Lets the assistant answer follow-ups without scanning the full history.
    """

    conversation = models.OneToOneField(
        Conversation, on_delete=models.CASCADE, related_name="context"
    )

    topics_discussed = models.JSONField(default=list)
    search_history = models.JSONField(default=list)
    location_mentions = models.JSONField(default=list)
    user_intent = models.CharField(max_length=50, blank=True)

    stage = models.CharField(
        max_length=20,
        default="initial",
        help_text="Lifecycle stage: initial / developing / ongoing.",
    )

    avg_response_time = models.FloatField(null=True, blank=True)
    successful_searches = models.IntegerField(default=0)
    failed_searches = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversation_contexts"

    # --------------------------------------------------------------------- #
    # Lightweight heuristics; heavy NLP should run in a background task.    #
    # --------------------------------------------------------------------- #
    def update_context(self) -> None:
        msgs = self.conversation.messages.all()
        self.topics_discussed = self._extract_topics(msgs)
        self.search_history = self._extract_search_history(msgs)
        self.location_mentions = self._extract_locations(msgs)
        self.stage = self._determine_stage(msgs)
        self.save(
            update_fields=[
                "topics_discussed",
                "search_history",
                "location_mentions",
                "stage",
            ]
        )

    # Basic keyword extraction ------------------------------------------- #
    @staticmethod
    def _extract_topics(messages) -> List[str]:
        topics: List[str] = []
        keywords_map = {
            "food": ["restaurant", "pizza", "burger", "eat"],
            "shopping": ["shop", "buy", "store", "mall"],
            "entertainment": ["movie", "cinema", "show", "event"],
        }
        for m in messages.filter(role=ConversationMessage.MessageRole.USER):
            content = m.content.lower()
            for topic, kws in keywords_map.items():
                if any(k in content for k in kws) and topic not in topics:
                    topics.append(topic)
        return topics

    @staticmethod
    def _extract_search_history(messages) -> List[str]:
        return list(
            messages.filter(
                role=ConversationMessage.MessageRole.USER,
                message_type=ConversationMessage.MessageType.SEARCH_QUERY,
            )
            .order_by("-created_at")
            .values_list("content", flat=True)[:5]
        )

    @staticmethod
    def _extract_locations(messages) -> List[str]:
        locs: List[str] = []
        keywords = ["near", "around", "close to", "in", "at"]
        for m in messages.filter(role=ConversationMessage.MessageRole.USER):
            words = m.content.lower().split()
            for k in keywords:
                if k in words:
                    try:
                        idx = words.index(k)
                        candidate = words[idx + 1]
                        if candidate not in locs:
                            locs.append(candidate)
                    except (ValueError, IndexError):
                        continue
        return locs

    @staticmethod
    def _determine_stage(messages) -> str:
        count = messages.count()
        if count <= 2:
            return "initial"
        if count <= 10:
            return "developing"
        return "ongoing"
