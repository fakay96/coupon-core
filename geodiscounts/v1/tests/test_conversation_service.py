import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from geodiscounts.models import Conversation, ConversationMessage, ConversationContext
from geodiscounts.v1.services.conversation_service import ConversationService

User = get_user_model()

@pytest.mark.django_db(databases=["default","geodiscounts_db","authentication_shard"])
@pytest.mark.asyncio
async def test_async_get_context_includes_history_and_location():
    user = User.objects.create_user(username="t", email="t@example.com", password="pass")
    conv = Conversation.objects.create(user=user, last_location=Point(1.0, 2.0), last_radius=1500)
    ConversationContext.objects.create(conversation=conv, search_history=["pizza", "shoes"], user_intent="searching")
    ConversationMessage.objects.create(
        conversation=conv,
        role=ConversationMessage.MessageRole.USER,
        message_type=ConversationMessage.MessageType.SEARCH_QUERY,
        content="pizza near me"
    )
    svc = ConversationService()
    context = await svc.async_get_context(conv)
    assert context["search_history"] == ["pizza", "shoes"]
    assert context["last_location"] == {"latitude": 2.0, "longitude": 1.0}
    assert context["last_radius"] == 1500
    assert context["count"] == 1

@pytest.mark.django_db(databases=["default","geodiscounts_db","authentication_shard"])
@pytest.mark.asyncio
async def test_async_get_recent_messages_returns_ordered_list():
    user = User.objects.create_user(username="t2", email="t2@example.com", password="pass")
    conv = Conversation.objects.create(user=user)
    ConversationMessage.objects.create(conversation=conv, role=ConversationMessage.MessageRole.USER, content="first")
    ConversationMessage.objects.create(conversation=conv, role=ConversationMessage.MessageRole.ASSISTANT, content="second")
    svc = ConversationService()
    msgs = await svc.async_get_recent_messages(conv, limit=2)
    assert msgs == ["first", "second"]
