# discountcrawlers/crawlers/pipelines.py
"""
===================================
Item pipeline definition with strong typing, docstrings, and utilities
extracted into helper functions.

Pipelines included:
- DiscountPipeline: Cleans and normalizes price/discount fields.
- DealsAndEmbedPipeline: Aggregates items, generates a summary and embedding
  using external APIs, and then safely writes the deals JSON and embedding
  file only after network operations are complete.
===================================
"""
from __future__ import annotations

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Protocol, List, Optional # Added List, Optional

from itemadapter import ItemAdapter
import httpx # For specific error catching if needed

# --- Local Utilities ---
# Assuming these exist in ./utils/
try:
    from .utils.price import (
        parse_discount_percentage,
        parse_euro_price,
    )
    from .utils.embedding import embed_text, save_embedding # Expects save_embedding(vec, path) -> bool
    from .utils.gemini_chat import chat # Expects async chat(prompt) -> str
except ImportError as e:
     # Provide a more helpful error if utils aren't found
    raise ImportError(
        f"Could not import utility functions: {e}. "
        "Ensure utils/price.py, utils/embedding.py, and utils/gemini_chat.py exist "
        "relative to pipelines.py and contain the required functions."
    ) from e

# --- Module Logger ---
# Use __name__ for logger to follow Python best practices
LOGGER = logging.getLogger(__name__)


# --- Protocol (Optional but good practice) ---
class SupportsMapping(Protocol):
    """Protocol modelling Scrapy items and dataclasses like DiscountData."""
    def items(self) -> Any:  # pragma: no cover
        ...


# --- Pipeline 1: Data Cleaning ---
class DiscountPipeline:
    """
    Clean and normalise scraped discount items.

    - Converts price strings (sale_price, original_price) to floats.
    - Normalises discount percentages (removes '%', converts to int).

    Enable via the ``ITEM_PIPELINES`` Scrapy setting, usually before
    pipelines that require numeric data or aggregation.
    """

    def process_item(
        self,
        item: Any, # Can be scrapy.Item or other dict-like object
        spider: "scrapy.Spider",
    ) -> Any:
        """
        Parse and normalise price and discount fields on a single item.

        Args:
            item: The scraped item to process.
            spider: The spider which scraped the item (used for logging).

        Returns:
            The same item, with cleaned and normalised fields.
        """
        adapter = ItemAdapter(item)
        item_url = adapter.get("url", "Unknown URL") # For logging context

        # ----- Price parsing -----
        for price_field in ("sale_price", "original_price"):
            original_value = adapter.get(price_field)
            try:
                # Pass the raw value to the parsing function
                parsed_price = parse_euro_price(original_value)
                adapter[price_field] = parsed_price
                # Optional: Log the change for debugging
                # if original_value is not None and parsed_price != original_value:
                #     LOGGER.debug(f"Parsed {price_field} for {item_url}: '{original_value}' -> {parsed_price}")
            except Exception as e:
                # Log error but allow item processing to continue with None
                LOGGER.error(f"Failed to parse {price_field} '{original_value}' for {item_url}: {e}")
                adapter[price_field] = None # Set to None on parsing error

        # ----- Discount % parsing -----
        original_discount = adapter.get("discount_percentage")
        try:
            parsed_discount = parse_discount_percentage(original_discount)
            adapter["discount_percentage"] = parsed_discount
            # Optional: Log the change
            # if original_discount is not None and parsed_discount != original_discount:
            #      LOGGER.debug(f"Parsed discount for {item_url}: '{original_discount}' -> {parsed_discount}")
        except Exception as e:
            LOGGER.error(f"Failed to parse discount_percentage '{original_discount}' for {item_url}: {e}")
            adapter["discount_percentage"] = None # Set to None on error

        # NOTE: Timestamp is added in the *next* pipeline (DealsAndEmbedPipeline)
        #       just before adding to the final list.

        return item


# --- Pipeline 2: Aggregation, Summary, Embedding, Safe File Write ---
class DealsAndEmbedPipeline:
    """
    Aggregate cleaned deals, generate summary & embedding via API calls,
    THEN safely write the collected deals JSON and the summary embedding file.

    This pipeline collects all cleaned items. On spider close, it:
    1. Serializes the collected deals to a JSON string *in memory*.
    2. Calls the Gemini Chat API to generate a concise summary of the deals.
    3. Calls the Gemini Embedding API to generate an embedding for the summary.
    4. **Only then**, writes the complete deals JSON string to the file specified
       by the `DEALS_JSON_PATH` setting.
    5. Saves the summary embedding vector (if successfully generated) to a
       `.emb.json` file next to the deals JSON.

    This order prevents corruption of the main deals JSON file if network
    API calls fail during the summary or embedding steps.

    Configuration:
        - Set `DEALS_JSON_PATH` in settings (default: "discounts.json").
        - Enable this pipeline **after** `DiscountPipeline` in `ITEM_PIPELINES`.
    """

    def open_spider(self, spider: "scrapy.Spider") -> None:
        """
        Initialize an empty list to store incoming deal items.

        Args:
            spider: The spider instance (used for logging).
        """
        self.deals: list[Mapping[str, Any]] = []
        spider.logger.info(f"{self.__class__.__name__} opened.")

    def process_item(self, item: Any, spider: "scrapy.Spider") -> Any:
        """
        Add a UTC timestamp and collect the processed item.

        Args:
            item: The cleaned item passed from the previous pipeline.
            spider: The spider instance (used for logging).

        Returns:
            The same item, unmodified after adding timestamp and appending.
        """
        adapter = ItemAdapter(item)
        # Add timestamp just before finalizing the item for this run
        adapter["timestamp"] = datetime.utcnow().isoformat(timespec="seconds")
        self.deals.append(dict(adapter)) # Store a dict copy
        return item

    def close_spider(self, spider: "scrapy.Spider") -> None:
        """
        Summarize deals, generate embedding, then write JSON and embedding file.
        Ensures file writing happens last to prevent corruption from API errors.

        Args:
            spider: The spider instance (used for settings and logging).
        """
        spider.logger.info(f"Closing spider. Processing {len(self.deals)} collected deals.")
        if not self.deals:
            spider.logger.warning("No deals collected, skipping summary, embedding, and file writing.")
            return

        # Get configured output path
        path = Path(spider.settings.get("DEALS_JSON_PATH", "discounts.json")).resolve()
        spider.logger.info(f"Output path set to: {path}")

        # Initialize results variables
        deals_json_string_to_write: Optional[str] = None
        summary: Optional[str] = None
        embedding_vector: Optional[List[float]] = None

        # --- Step 1: Prepare the full JSON string in memory ---
        try:
            deals_json_string_to_write = json.dumps(self.deals, ensure_ascii=False, indent=2)
            spider.logger.debug(f"Successfully serialized {len(self.deals)} deals to JSON string in memory.")
        except Exception:
            # Use logger that includes traceback automatically
            LOGGER.exception("CRITICAL: Failed to serialize deals to JSON string in memory. Cannot write file.")
            return # Cannot proceed if serialization fails

        # --- Step 2: Generate Summary (Network Call 1) ---
        # Construct prompt carefully, potentially using only a sample if deals_json_string is huge
        # Consider adding token count check if needed
        summarization_prompt = f"""
Du bist ein Datenanalyst. Fasse die wichtigsten Merkmale der Produktangebote in den folgenden JSON-Daten zusammen.

JSON_DATEN:
{deals_json_string_to_write}

Anweisungen:
Konzentriere dich auf die Produkttypen, bekannte Marken, typische Preisspannen und Rabattniveaus. Halte die Zusammenfassung kurz (z.B. 1-2 Absätze). Antworte auf Deutsch.
"""
        try:
            spider.logger.info("Generating summary of deals via Gemini Chat API...")
            # Ensure 'chat' is the imported async function
            summary = asyncio.run(chat(summarization_prompt))
            if summary and not summary.startswith("[Fehler"): # Basic check for error messages from chat()
                spider.logger.info("Summary generated successfully.")
                # spider.logger.debug(f"Generated Summary: {summary}")
            else:
                 spider.logger.error(f"Summary generation failed or returned error: {summary}")
                 summary = None # Ensure summary is None if it failed or returned error msg
        except Exception as e:
            LOGGER.exception("Failed to generate summary via Gemini Chat API:")
            spider.logger.error(f"Summary generation failed. Proceeding without summary/embedding.")
            summary = None # Ensure summary is None if an exception occurred

        # --- Step 3: Generate Embedding (Network Call 2) ---
        # Only attempt embedding if the summary was successful
        if summary:
            try:
                spider.logger.info("Generating embedding for the summary via Gemini Embedding API...")
                 # Ensure 'embed_text' is the imported async function
                embedding_vector = asyncio.run(embed_text(summary, task_type="RETRIEVAL_DOCUMENT"))

                if embedding_vector: # embed_text returns List or None
                     spider.logger.info(f"Embedding for summary generated successfully (dimension: {len(embedding_vector)}).")
                else:
                     spider.logger.error("Embedding generation call returned None (likely an API or internal error).")
                     embedding_vector = None # Ensure it's None

            except Exception as e:
                LOGGER.exception("Failed to generate embedding for summary:")
                spider.logger.error(f"Embedding generation failed. Proceeding without saving embedding.")
                embedding_vector = None # Ensure vector is None if embedding fails
        else:
            spider.logger.warning("Skipping embedding generation as summary failed or was not generated.")

        # --- Step 4: Write Files (Safely, After Network Calls) ---
        # Write the main deals JSON file
        try:
            spider.logger.info(f"Attempting to write {len(self.deals)} deals to {path}...")
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(deals_json_string_to_write, encoding="utf-8")
            spider.logger.info(f"Successfully wrote deals JSON to {path}")
        except IOError as e:
            LOGGER.exception(f"CRITICAL: Failed to write final deals JSON to {path}:")
            # If this critical step fails, the data is lost for this run
            return # Stop here

        # Write the embedding file ONLY if the vector was successfully generated
        if embedding_vector:
            emb_path = path.with_suffix('.emb.json')
            spider.logger.info(f"Attempting to write summary embedding to {emb_path}...")
            # Assuming save_embedding handles its own errors and returns True/False
            if save_embedding(embedding_vector, path):
                 spider.logger.info("Successfully wrote summary embedding file.")
            else:
                 # save_embedding should have logged the specific error
                 spider.logger.error("Failed to save summary embedding file (check previous logs).")
        else:
            spider.logger.info("Skipping embedding file write as vector was not generated.")

        spider.logger.info(f"{self.__class__.__name__} finished.")