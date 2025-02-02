from __future__ import annotations as _annotations

import os
import asyncio
import httpx
import logfire
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import List

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI
from supabase import Client

load_dotenv()

# Configure the LLM model (default to gpt-4o-mini if not set)
llm = os.getenv("LLM_MODEL", "gpt-4o-mini")
model = OpenAIModel(llm)

# Configure logfire if needed
logfire.configure(send_to_logfire='if-token-present')


@dataclass
class DishpalAIDeps:
    """
    Dependencies needed by the Dishpal AI agent,
    specifically the Supabase client and the OpenAI client.
    """
    supabase: Client
    openai_client: AsyncOpenAI


# System prompt: focusing on retrieving discount chunk data
system_prompt = """
You are Dishpal AI, an agent specialized in retrieving discount information from a Supabase table named 'discounts_data'.
You can:
 - Retrieve relevant discount chunks for a user query using vector similarity.
 - List or inspect existing URLs or chunk data in the database.
 - Provide details for a specific discount URL by combining all chunk data.

If you cannot find relevant discount data, politely indicate that none was found.
Do not provide answers unrelated to discount retrieval.
"""

# Create the Dishpal AI agent
dishpal_ai_expert = Agent(
    model=model,
    system_prompt=system_prompt,
    deps_type=DishpalAIDeps,
    retries=2
)

async def get_embedding(text: str, openai_client: AsyncOpenAI) -> List[float]:
    """
    Get embedding vector from OpenAI. Adjust 'text-embedding-3-small' if needed.
    """
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[Embedding Error] {e}")
        # Return a zero vector if there's an error
        return [0.0] * 1536


@dishpal_ai_expert.tool
async def retrieve_relevant_discounts(ctx: RunContext[DishpalAIDeps], user_query: str) -> str:
    """
    Retrieve the top 5 relevant discount chunks from 'discounts_data' using vector similarity.
    
    Args:
        ctx: The RunContext (includes supabase and openai_client).
        user_query: The user's text describing what discount or product they need.
    
    Returns:
        A formatted string containing the top 5 chunks that match the user's query.
    """
    try:
        # 1) Generate embedding from user query
        query_embedding = await get_embedding(user_query, ctx.deps.openai_client)

        # 2) Call Supabase RPC 'match_discounts_chunks'
        #    We pass an empty filter {} unless you want to filter further.
        result = ctx.deps.supabase.rpc(
            'match_discounts_chunks',
            {
                'query_embedding': query_embedding,
                'match_count': 5,
                'filter': {}  # or e.g. {"website": "fromaustria"} if you store that in metadata
            }
        ).execute()

        if not result.data:
            return "No relevant discount data found."

        # 3) Format the result
        chunks_output = []
        for row in result.data:
            chunk_text = (
                f"**Title**: {row['title']}\n"
                f"**Summary**: {row['summary']}\n"
                f"**Content**: {row['content']}\n\n"
                f"**Retailer**: {row['retailer'] or 'Unknown'}\n"
                f"**Product**: {row['product_name'] or 'Unknown'}\n"
                f"**Category**: {row['category'] or 'Unknown'}\n"
                f"**Original Price**: {row['original_price']}\n"
                f"**Discounted Price**: {row['discounted_price']}\n"
                f"**Discount (%)**: {row['discount_percentage']}\n"
                f"**Valid From**: {row['valid_from']}\n"
                f"**Valid Until**: {row['valid_until']}\n"
                f"**Stock**: {row['stock_status']}\n"
                f"---"
            )
            chunks_output.append(chunk_text)

        return "\n\n".join(chunks_output)

    except Exception as e:
        print(f"[retrieve_relevant_discounts] Error: {e}")
        return f"Error retrieving discount data: {str(e)}"


@dishpal_ai_expert.tool
async def list_discount_urls(ctx: RunContext[DishpalAIDeps]) -> List[str]:
    """
    Retrieve a sorted list of unique URLs from the 'discounts_data' table.
    
    Returns:
        List of URLs
    """
    try:
        result = (
            ctx.deps.supabase
            .from_("discounts_data")
            .select("url")
            .execute()
        )

        if not result.data:
            return []

        # Create a unique set of URLs
        urls = sorted(set(row["url"] for row in result.data if row["url"]))
        return urls

    except Exception as e:
        print(f"[list_discount_urls] Error: {e}")
        return []


@dishpal_ai_expert.tool
async def get_discount_content_by_url(ctx: RunContext[DishpalAIDeps], url: str) -> str:
    """
    Retrieve all chunks for a specific discount URL and combine them in chunk_number order.
    
    Args:
        ctx: The DishpalAIDeps context (supabase, openai_client).
        url: The URL of the product/discount page to retrieve.
    
    Returns:
        A string combining all chunk content in ascending chunk_number order.
    """
    try:
        # Query all chunk data for this URL
        result = (
            ctx.deps.supabase
            .from_("discounts_data")
            .select("title, summary, content, chunk_number")
            .eq("url", url)
            .order("chunk_number")
            .execute()
        )

        if not result.data:
            return f"No discount content found for URL: {url}"

        # Combine the chunks
        # We'll assume all chunks have a similar or identical title/summary but show them anyway
        combined_output = []
        for chunk in result.data:
            chunk_str = (
                f"# Chunk {chunk['chunk_number']} - {chunk['title']}\n"
                f"Summary: {chunk['summary']}\n\n"
                f"{chunk['content']}\n"
            )
            combined_output.append(chunk_str)

        return "\n\n---\n\n".join(combined_output)

    except Exception as e:
        print(f"[get_discount_content_by_url] Error: {e}")
        return f"Error retrieving discount content for {url}: {str(e)}"
