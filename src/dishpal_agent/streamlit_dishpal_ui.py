from __future__ import annotations
from typing import Literal, TypedDict
import asyncio
import os
import json

import streamlit as st
import logfire
from supabase import Client
from openai import AsyncOpenAI

# Pydantic AI message classes (still used internally for the agent's conversation)
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    RetryPromptPart,
    ModelMessagesTypeAdapter
)

# Import your Dishpal AI agent & dependencies
from dishpal_ai_expert import dishpal_ai_expert, DishpalAIDeps

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Create Supabase & OpenAI clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Configure logfire (optional)
logfire.configure(send_to_logfire='never')


class ChatMessage(TypedDict):
    """Format of messages sent to the browser/UI."""
    role: Literal['user', 'model']
    timestamp: str
    content: str


def display_message_part(part):
    """
    Display a single part of a conversation message in Streamlit.
    Could be system prompts, user prompts, or assistant text.
    """
    if part.part_kind == 'system-prompt':
        with st.chat_message("system"):
            st.markdown(f"**System**: {part.content}")
    elif part.part_kind == 'user-prompt':
        with st.chat_message("user"):
            st.markdown(part.content)
    elif part.part_kind == 'text':
        with st.chat_message("assistant"):
            st.markdown(part.content)


async def run_agent_with_streaming(user_input: str):
    """
    Run the Dishpal AI agent with streaming text for the user_input prompt.
    Keep track of conversation in st.session_state.messages.
    """
    # Construct the DishpalAIDeps with current supabase and openai_client
    deps = DishpalAIDeps(
        supabase=supabase,
        openai_client=openai_client
    )

    # Start the streaming run
    async with dishpal_ai_expert.run_stream(
        user_input,
        deps=deps,
        message_history=st.session_state.messages[:-1],  # pass entire conversation so far
    ) as result:
        partial_text = ""
        message_placeholder = st.empty()

        # Stream partial text from the agent
        async for chunk in result.stream_text(delta=True):
            partial_text += chunk
            message_placeholder.markdown(partial_text)

        # Exclude any user-prompt messages from the new messages
        filtered_messages = [
            msg for msg in result.new_messages()
            if not any(part.part_kind == 'user-prompt' for part in msg.parts)
        ]
        st.session_state.messages.extend(filtered_messages)

        # Finally add the completed response
        st.session_state.messages.append(
            ModelResponse(parts=[TextPart(content=partial_text)])
        )


def fetch_discounts_data() -> list[dict]:
    """
    Retrieve some discount rows from the 'discounts_data' table
    for a quick demo of what's in the DB. Adjust limit or filtering as needed.
    """
    try:
        response = supabase.from_("discounts_data").select("*").limit(20).execute()
        if response.data:
            return response.data
        return []
    except Exception as e:
        st.error(f"[Fetch Error] {e}")
        return []


def display_discounts_table(discount_rows: list[dict]):
    """
    Display discount data in a simple table or card format.
    You can adapt to show columns like product_name, original_price, etc.
    """
    if not discount_rows:
        st.info("No discount data found in 'discounts_data'.")
        return

    st.subheader("Sample Discount Data")
    for row in discount_rows:
        st.markdown("---")
        st.markdown(f"**URL**: {row.get('url')}")
        st.markdown(f"**Title**: {row.get('title')}")
        st.markdown(f"**Summary**: {row.get('summary')}")
        st.markdown(f"**Content**: {row.get('content')[:200]}...")  # truncated
        st.markdown(f"**Retailer**: {row.get('retailer')}")
        st.markdown(f"**Product**: {row.get('product_name')}")
        st.markdown(f"**Original Price**: {row.get('original_price')}")
        st.markdown(f"**Discounted Price**: {row.get('discounted_price')}")
        st.markdown(f"**Discount (%)**: {row.get('discount_percentage')}")
        st.markdown(f"**Valid From**: {row.get('valid_from')}")
        st.markdown(f"**Valid Until**: {row.get('valid_until')}")
        st.markdown(f"**Stock Status**: {row.get('stock_status')}")


async def main():
    # Page branding for Dishpal AI
    st.title("Dishpal AI: Discount Retrieval")
    st.write("Ask me about discounts! This interface is powered by Dishpal AI + Supabase + OpenAI.")

    # 1. Initialize conversation
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 2. Display conversation so far
    for msg in st.session_state.messages:
        if isinstance(msg, (ModelRequest, ModelResponse)):
            for part in msg.parts:
                display_message_part(part)

    # 3. Chat input
    user_input = st.chat_input("Ask about discounts, retailers, or product info:")
    if user_input:
        st.session_state.messages.append(
            ModelRequest(parts=[UserPromptPart(content=user_input)])
        )
        with st.chat_message("user"):
            st.markdown(user_input)

        # Stream the AI response
        with st.chat_message("assistant"):
            await run_agent_with_streaming(user_input)

    # 4. Display sample discount data from 'discounts_data'
    st.write(" ")
    st.write("## Browse Sample Discount Data")
    discount_rows = fetch_discounts_data()
    display_discounts_table(discount_rows)


if __name__ == "__main__":
    asyncio.run(main())
