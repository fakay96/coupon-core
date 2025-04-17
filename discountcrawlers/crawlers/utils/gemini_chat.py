# utils/gemini_chat.py
import httpx
import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv() # Load environment variables from .env file
LOGGER = logging.getLogger(__name__)

_GEMINI_KEY = os.getenv("GEMINI_API_KEY")
_CHAT_MODEL_NAME = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash-latest") # Use env var or default

if not _GEMINI_KEY:
    # This check prevents running without a key
    raise ValueError("GEMINI_API_KEY environment variable not set or .env file not loaded.")

_CHAT_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_CHAT_MODEL_NAME}:generateContent"
    f"?key={_GEMINI_KEY}"
)
_HEADERS = {"Content-Type": "application/json"}
_DEFAULT_TIMEOUT = 120 # Seconds for chat generation

# Default safety settings (adjust if necessary)
_DEFAULT_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Default generation config (adjust if necessary)
_DEFAULT_GENERATION_CONFIG = {
     "temperature": 0.7,
     "maxOutputTokens": 2048, # Increased token limit
}


async def chat(
    prompt: str,
    safety_settings: Optional[List[Dict[str, Any]]] = None,
    generation_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Sends a prompt to the configured Gemini chat model and returns the text response.

    Args:
        prompt: The user prompt or instruction for the LLM.
        safety_settings: Optional safety settings override.
        generation_config: Optional generation config override.

    Returns:
        The text part of the LLM's response, or an error message string.

    Raises:
        Exception: Propagates exceptions from HTTP requests or severe API errors.
    """
    if not prompt or not prompt.strip():
        LOGGER.warning("Received empty prompt for chat.")
        return "[Fehler: Leere Anfrage erhalten]" # Error in German

    current_safety = safety_settings if safety_settings is not None else _DEFAULT_SAFETY_SETTINGS
    current_config = generation_config if generation_config is not None else _DEFAULT_GENERATION_CONFIG

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": current_safety,
        "generationConfig": current_config
    }

    async with httpx.AsyncClient(http2=True, timeout=_DEFAULT_TIMEOUT) as cli:
        try:
            LOGGER.debug(f"Sending request to Gemini Chat API ({_CHAT_MODEL_NAME})...")
            # Avoid logging the full payload if it contains sensitive data or is very large
            # LOGGER.debug(f"Payload (preview): {json.dumps(payload)[:500]}...")

            r = await cli.post(_CHAT_API_URL, headers=_HEADERS, json=payload)
            r.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            response_data = r.json()
            LOGGER.debug("Received successful response from Chat API.")

            # --- Parse Response ---
            if not response_data.get("candidates"):
                # Check for prompt feedback block reason first
                feedback = response_data.get("promptFeedback", {})
                block_reason = feedback.get("blockReason")
                if block_reason:
                    LOGGER.warning(f"Gemini API blocked response. Reason: {block_reason}")
                    safety_ratings_info = feedback.get("safetyRatings", "N/A")
                    return f"[Inhalt blockiert: {block_reason}. Ratings: {safety_ratings_info}]"
                else:
                    LOGGER.error(f"Gemini API response missing 'candidates'. Full response: {response_data}")
                    return "[Fehler: Unerwartete Antwortstruktur von der API (keine Kandidaten)]"

            candidates = response_data.get("candidates", [])
            if candidates and candidates[0].get("content", {}).get("parts", []):
                 # Successfully found text part
                response_text = candidates[0]["content"]["parts"][0]["text"]
                LOGGER.debug(f"Extracted response text (preview): {response_text[:200]}...")
                return response_text
            else:
                # Content might be missing due to finish reason (e.g., safety, length)
                finish_reason = candidates[0].get("finishReason", "UNKNOWN")
                safety_ratings = candidates[0].get("safetyRatings", "N/A")
                LOGGER.warning(
                    f"Chat response candidate missing content/parts. "
                    f"Finish Reason: {finish_reason}, Safety Ratings: {safety_ratings}"
                 )
                if finish_reason != "STOP":
                    return f"[Antwort unvollständig/blockiert. Grund: {finish_reason}]"
                else:
                     return "[Fehler: Konnte Text nicht aus gültiger API-Antwort extrahieren]"

        except httpx.HTTPStatusError as e:
            # Log details from the error response if possible
            error_message = f"Chat API Error {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_details = error_data.get("error", {}).get("message", e.response.text)
                error_message += f": {error_details}"
            except Exception:
                error_message += f": {e.response.text}" # Fallback to raw text
            LOGGER.exception(f"HTTP Error during chat request: {error_message}")
            # Re-raise a clearer exception for the caller
            raise Exception(error_message) from e
        except httpx.RequestError as e:
            LOGGER.exception(f"Network error during chat request: {e}")
            raise Exception(f"Network error communicating with Chat API: {e}") from e
        except json.JSONDecodeError as e:
            # Handle cases where API returns non-JSON response (e.g., HTML error pages)
            LOGGER.exception(f"Failed to decode JSON response from chat API. Response text: {e.doc}")
            raise Exception(f"Invalid JSON received from Chat API: {e.doc[:500]}...") from e
        except Exception as e:
            LOGGER.exception("An unexpected error occurred during the chat request:")
            raise # Re-raise other unexpected errors


async def extract_relevant_json(conversation_summary: str, deals_json_str: str) -> Optional[str]:
    """
    Asks the LLM to extract relevant JSON data based on the conversation.

    Args:
        conversation_summary: A summary of the successful query and answer.
        deals_json_str: The original full JSON string of all deals.

    Returns:
        A string containing the extracted JSON list, or None if extraction fails
        or no relevant items are identified.
    """
    LOGGER.info("Attempting to extract relevant JSON data via LLM...")
    extraction_prompt = f"""
Act as a data extraction tool. Based *only* on the following summary of a user interaction and the provided complete DEALS_JSON, extract the full JSON objects for the **specific products** that the user expressed satisfaction with or that directly answer their final confirmed query.

"""