
import httpx
import os
import json
import logging
import math
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# --- Local Import ---
# Need the 'chat' function for the RAG part
try:
    from .gemini_chat import chat
except ImportError:
    # Fallback if run directly or structure issues
    try:
        from gemini_chat import chat
    except ImportError:
         # This will cause answer_query to fail later if chat isn't found
        chat = None
        logging.error("Could not import 'chat' function for RAG.")

# --- Configuration ---
load_dotenv()
LOGGER = logging.getLogger(__name__)

_GEMINI_KEY = os.getenv("GEMINI_API_KEY")
# Allow configuration via env var, provide a default stable model
_EMB_MODEL_NAME = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")

if not _GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set or .env file not loaded.")
if chat is None:
     LOGGER.warning("Chat function not loaded, RAG functionality in answer_query will fail.")

_EMB_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_EMB_MODEL_NAME}:embedContent"
    f"?key={_GEMINI_KEY}"
)
_HEADERS = {"Content-Type": "application/json"}
_EMB_TIMEOUT = 60 # Seconds

# --- Greeting Keywords ---
GREETING_KEYWORDS_EN = {"hello", "hi", "hey", "yo", "greetings", "good morning", "good afternoon", "good evening"}
GREETING_KEYWORDS_DE = {"hallo", "servus", "guten tag", "moin", "grüß gott", "tag", "guten morgen", "guten abend"}
ALL_GREETING_KEYWORDS = GREETING_KEYWORDS_EN.union(GREETING_KEYWORDS_DE)

# --- Embedding Functions ---

async def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[List[float]]:
    """
    Generates an embedding for the given text using the configured Gemini model.

    Args:
        text: The text to embed.
        task_type: The intended task for the embedding (e.g., RETRIEVAL_QUERY,
                   RETRIEVAL_DOCUMENT, SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING).

    Returns:
        A list of floats representing the embedding, or None if an error occurs.
    """
    if not text or not text.strip():
        LOGGER.warning("Attempted to embed empty or whitespace-only text.")
        return None

    payload: Dict[str, Any] = {
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
    }
    # Some models/tasks benefit from a title, add if needed, e.g.:
    # if task_type == "RETRIEVAL_DOCUMENT":
    #     payload["title"] = "Product Deal Information"

    # Basic length check (actual limit is token-based and model-specific)
    # Refer to Google's documentation for the specific model's limit
    MAX_CHARS_GUESS = 8000
    if len(text) > MAX_CHARS_GUESS:
        LOGGER.warning(f"Input text exceeds {MAX_CHARS_GUESS} chars, truncating for embedding. Actual limit is token-based.")
        payload["content"]["parts"][0]["text"] = text[:MAX_CHARS_GUESS]

    async with httpx.AsyncClient(http2=True, timeout=_EMB_TIMEOUT) as cli:
        try:
            LOGGER.debug(f"Sending request to Gemini Embedding API ({_EMB_MODEL_NAME})...")
            r = await cli.post(_EMB_API_URL, headers=_HEADERS, json=payload)
            r.raise_for_status()
            response_data = r.json()
            LOGGER.debug("Received successful response from Embedding API.")

            # Extract embedding values
            embedding_data = response_data.get("embedding")
            if embedding_data and "values" in embedding_data:
                return embedding_data["values"]
            else:
                LOGGER.error(f"Embedding API response missing 'embedding.values'. Response: {response_data}")
                return None

        except httpx.HTTPStatusError as e:
            error_message = f"Embedding API Error {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_details = error_data.get("error", {}).get("message", e.response.text)
                error_message += f": {error_details}"
            except Exception:
                error_message += f": {e.response.text}"
            LOGGER.exception(f"HTTP Error during embedding request: {error_message}")
            # Don't raise, return None to allow caller to handle
            return None
        except httpx.RequestError as e:
            LOGGER.exception(f"Network error during embedding request: {e}")
            return None
        except json.JSONDecodeError as e:
             LOGGER.exception(f"Failed to decode JSON response from embedding API. Response text: {e.doc}")
             return None
        except Exception as e:
            LOGGER.exception("An unexpected error occurred during text embedding:")
            return None


def save_embedding(vec: List[float], path: Path) -> bool:
    """Saves the embedding vector to a JSON file alongside the original path."""
    emb_path = path.with_suffix(".emb.json")
    try:
        with emb_path.open("w", encoding="utf-8") as f:
            json.dump(vec, f)
        LOGGER.info(f"Saved embedding to {emb_path}")
        return True
    except (IOError, TypeError) as e:
        LOGGER.exception(f"Failed to save embedding to {emb_path}: {e}")
        return False


def load_embedding(path: Path) -> Optional[List[float]]:
    """Loads the embedding vector from its JSON file."""
    emb_path = path.with_suffix(".emb.json")
    if not emb_path.is_file():
        LOGGER.warning(f"Embedding file not found: {emb_path}")
        return None
    try:
        with emb_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and all(isinstance(x, (float, int)) for x in data):
                 return data
            else:
                 LOGGER.error(f"Invalid data format in embedding file {emb_path}. Expected list of numbers.")
                 return None
    except (IOError, json.JSONDecodeError) as e:
        LOGGER.exception(f"Failed to load or parse embedding from {emb_path}: {e}")
        return None


def cosine_similarity(a: Optional[List[float]], b: Optional[List[float]]) -> float:
    """Calculates cosine similarity between two vectors, handling None inputs."""
    if a is None or b is None or not a or not b:
        LOGGER.debug("Cosine similarity input missing or empty, returning 0.0")
        return 0.0

    if len(a) != len(b):
        LOGGER.warning(f"Attempting cosine similarity on vectors of different dimensions: {len(a)} vs {len(b)}. Returning 0.0.")
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    denominator = norm_a * norm_b
    if denominator < 1e-9: # Avoid division by zero
        LOGGER.debug("One or both vectors have zero magnitude in cosine similarity.")
        # If dot product is also zero, vectors are orthogonal (or one is zero).
        # If dot product is non-zero, it means both vectors are zero (shouldn't happen with sqrt check)
        # or something numerically unstable occurred. Return 0.
        return 0.0
    else:
        similarity = dot / denominator
        # Clamp result to [-1, 1] due to potential floating point inaccuracies
        return max(-1.0, min(1.0, similarity))

# --- RAG Logic Function ---

async def answer_query(prompt: str, cache_path: Path) -> str:
    """
    Handles user queries using RAG:
    1. Responds to simple greetings directly.
    2. Checks semantic similarity of the query to the deals summary embedding.
    3. If similar enough, calls the chat LLM with the query and full deals context.
    4. If not similar, or if summary embedding is missing, provides relevant feedback.
    """
    if chat is None: # Check if chat function was imported
         return "[Interner Fehler: Chat-Funktion nicht verfügbar]"

    normalized_prompt = prompt.strip().lower()

    # --- Step 1: Check for Greetings ---
    is_greeting = False
    # Check exact match first
    if normalized_prompt in ALL_GREETING_KEYWORDS:
        is_greeting = True
    else:
        # Check if prompt *starts* with a greeting word + separator
        for keyword in ALL_GREETING_KEYWORDS:
            if (normalized_prompt.startswith(keyword + " ") or
                normalized_prompt.startswith(keyword + "!") or
                normalized_prompt.startswith(keyword + ".")):
                is_greeting = True
                break

    if is_greeting:
        LOGGER.info("Detected greeting, providing standard response.")
        return "Hallo! Ich bin Ihr Einkaufsassistent für fromaustria.com Angebote. Womit kann ich Ihnen helfen?"

    # --- Step 2: Load context and check summary embedding ---
    LOGGER.info(f"Processing query: '{prompt}'")
    if not cache_path.is_file():
        return "[Fehler: Angebotsdatei nicht gefunden]"

    try:
        # Load full deals JSON - needed for the final RAG prompt context
        deals_json_string = cache_path.read_text(encoding="utf-8")
    except Exception as e:
        LOGGER.exception(f"Failed to read deals file {cache_path}:")
        return "[Fehler beim Lesen der Angebotsdaten]"

    # Load the *summary* embedding for similarity check
    summary_vec = load_embedding(cache_path)

    # --- Step 3: Embed Prompt and Check Similarity (if summary_vec exists) ---
    prompt_vec: Optional[List[float]] = None
    similarity: float = 0.0
    proceed_to_rag = False
    SIMILARITY_THRESHOLD = 0.5 # Adjust this threshold based on testing

    if summary_vec:
        LOGGER.debug("Attempting to embed user prompt...")
        prompt_vec = await embed_text(prompt, task_type="RETRIEVAL_QUERY")

        if prompt_vec:
            similarity = cosine_similarity(prompt_vec, summary_vec)
            LOGGER.info(f"Similarity between prompt and deals summary: {similarity:.3f}")
            if similarity >= SIMILARITY_THRESHOLD:
                LOGGER.info("Similarity above threshold, proceeding to RAG.")
                proceed_to_rag = True
            else:
                LOGGER.info("Similarity below threshold.")
                # Don't proceed to RAG based on similarity check
                return "Das scheint nicht direkt mit den zusammengefassten Angeboten zusammenzuhängen. Können Sie Ihre Frage zu Produkten oder Rabatten präzisieren?"
        else:
            LOGGER.error("Failed to embed user prompt. Cannot perform similarity check.")
            # Decide how to handle this - maybe fallback to direct RAG?
            # For now, return an error message.
            return "[Fehler bei der Verarbeitung Ihrer Anfrage (Embedding fehlgeschlagen)]"
    else:
        # Summary embedding is missing - cannot check similarity.
        LOGGER.warning("Summary embedding not found. Proceeding directly to RAG call without similarity pre-check.")
        proceed_to_rag = True # Fallback: attempt RAG anyway

    # --- Step 4: Call Chat LLM for RAG (if similarity check passed or fallback) ---
    if proceed_to_rag:
        LOGGER.debug("Constructing RAG prompt for chat LLM...")
        # Use the refined RAG prompt from previous discussions
        rag_prompt = f"""
                    Du bist ein hilfreicher Einkaufsassistent. Deine Aufgabe ist es, Fragen zu Produktangeboten zu beantworten, die in den folgenden JSON-Daten enthalten sind.

                    **Anweisungen:**
                    1.  Lies die Frage des Benutzers sorgfältig durch: "{prompt}"
                    2.  Wenn die Frage allgemein ist (z.B. "Was gibt es für Angebote?", "Kannst du helfen?"), antworte freundlich, erkläre kurz, welche Art von Angebotsdaten du hast (z.B. Marken, Produkttypen), und **frage den Benutzer, wonach er genau sucht**. Gib **keine spezifischen Produktbeispiele** in dieser allgemeinen Antwort.
                    3.  Wenn der Benutzer nach bestimmten Produkten, Marken, Preisen oder Rabatten fragt, durchsuche die JSON-Daten und beantworte die Frage so genau wie möglich. **Nur dann** gib spezifische Beispiele aus den Daten an (Name, Marke, Preis, Rabatt falls vorhanden).
                    4.  Wenn die Frage des Benutzers nichts mit den Angeboten in den JSON-Daten zu tun hat, weise höflich darauf hin.
                    5.  Antworte immer auf Deutsch.

                    **Komplette Angebotsdaten (DEALS_JSON):**
                    ```json
                    {deals_json_string}"""