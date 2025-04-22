"""Localization resources for messaging and prompts.

Provides language mappings and formatting helpers.
"""

import logging
from typing import Any, Dict

LANG_NAMES: Dict[str, str] = {
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
}

GREETINGS: Dict[str, str] = {
    "en": "Hello! I'm your shopping assistant for deals. How can I help you?",
    "de": "Hallo! Ich bin Ihr Einkaufsassistent für Angebote. Womit kann ich Ihnen helfen?",
    "es": "¡Hola! Soy tu asistente de compras para ofertas. ¿En qué puedo ayudarte?",
    "fr": "Bonjour! Je suis votre assistant d'achat pour les offres. Comment puis-je vous aider?",
}

def get_string(
    key: Dict[str, str],
    lang_code: str,
    default_lang: str="en",
    **kwargs: Any,
) -> str:
    """Retrieve and format a localized string.

    Args:
        key: mapping of language codes to template strings.
        lang_code: desired language code.
        default_lang: fallback code.
        **kwargs: format args.

    Returns:
        Formatted localized string.
    """
    code = lang_code.lower() if lang_code else default_lang
    message = key.get(code) or key.get(default_lang, "")
    try:
        return message.format(**kwargs)
    except Exception:
        logging.warning("Localization formatting failed for %s", code)
        return message
