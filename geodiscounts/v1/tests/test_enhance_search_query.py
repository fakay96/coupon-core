import pytest
from types import SimpleNamespace
from geodiscounts.v1.views.geodiscount_views import ConversationalDiscountView

@pytest.mark.asyncio
async def test_enhance_search_query_parses_json():
    view = ConversationalDiscountView()
    view.gemini_client.async_generate_content = pytest.AsyncMock(return_value=SimpleNamespace(text='{"enhanced_query":"pizza","search_type":"general","confidence":0.9,"category":{"name":"food","confidence":0.8},"suggested_filters":{"price_range":{"min":0,"max":100},"brand":"Brand"}}'))
    result = await view._enhance_search_query("pizza", {}, [])
    assert result["query"] == "pizza"
    assert result["category"]["name"] == "food"
    assert result["filters"]["price_range"]["max"] == 100

@pytest.mark.asyncio
async def test_enhance_search_query_handles_invalid_json():
    view = ConversationalDiscountView()
    view.gemini_client.async_generate_content = pytest.AsyncMock(return_value=SimpleNamespace(text='not json'))
    result = await view._enhance_search_query("pizza", {}, [])
    assert result["category"]["name"] == "other"
    assert result["search_type"] == "general"
