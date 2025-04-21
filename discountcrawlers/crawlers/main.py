# query_deals.py (Interactive loop, handles greetings gracefully)
import argparse
import asyncio
import logging
from pathlib import Path
import sys
import json

# --- Imports for Helper Functions (Adjust paths if needed) ---
try:
    from utils.embedding import answer_query
    from utils.gemini_chat import chat, extract_relevant_json
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print(f"ERROR: Could not import necessary functions ({e}). Check utils/ paths.", file=sys.stderr)
    sys.exit(1)
# ---------------------------------------------------------

# --- Constants ---
# Define the standard greeting response string from answer_query exactly
STANDARD_GREETING_RESPONSE = "Hallo! Ich bin Ihr Einkaufsassistent für fromaustria.com Angebote. Womit kann ich Ihnen helfen?"


# Configure basic logging
logging.basicConfig(
    level=logging.INFO, # Change to DEBUG for detailed prompts/responses
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
LOGGER = logging.getLogger("query_deals")


async def main():
    """
    Manages the interactive conversation loop for querying deals, including
    feedback and optional JSON extraction. Handles greetings without exiting.
    """
    parser = argparse.ArgumentParser(
        description="Query scraped discount deals using Gemini RAG (interactive)."
    )
    parser.add_argument(
        "-d", "--deals-file",
        type=Path,
        required=True,
        help="Path to the scraped discounts JSON file (e.g., discounts.json)."
    )
    args = parser.parse_args()

    # --- Validate deals file ---
    deals_path: Path = args.deals_file.resolve()
    embedding_path = deals_path.with_suffix(".emb.json")

    if not deals_path.is_file():
        LOGGER.error(f"Deals file not found or is not a file: {deals_path}")
        sys.exit(1)
    if not embedding_path.is_file():
        LOGGER.error(f"Embedding file not found or is not a file (expected): {embedding_path}")
        LOGGER.error("Please ensure the crawler ran successfully and generated the summary embedding.")
        sys.exit(1)

    LOGGER.info(f"Using deals file: {deals_path}")

    # Load the full deals JSON once
    try:
        deals_json_string = deals_path.read_text(encoding='utf-8')
        _ = json.loads(deals_json_string)
    except Exception as e:
        LOGGER.exception(f"Failed to read or parse deals file {deals_path}:")
        sys.exit(1)

    # --- Conversation Loop ---
    conversation_history = [] # Store tuples of (user_utterance, assistant_answer)
    current_llm_prompt = ""
    max_iterations = 10 # Allow more turns
    iteration = 0

    print("\nWelcome to the Discount Deals Assistant!")
    print("Type 'quit' anytime to exit.")

    while iteration < max_iterations:
        iteration += 1
        print("\n" + "="*40 + f" Turn {iteration} " + "="*40)
        LOGGER.debug(f"Conversation Iteration {iteration}")

        # --- Determine Prompt for User ---
        if not conversation_history:
            prompt_message = "Enter your question about the deals:"
        # Check if the LAST assistant message was the standard greeting
        elif conversation_history[-1][1] == STANDARD_GREETING_RESPONSE:
             prompt_message = "Please enter your actual question about the deals:"
        else:
            prompt_message = "Is this answer helpful? ('yes' to finish & extract | 'no' | 'quit' | or provide more details/follow-up question):"

        # --- Get User Input ---
        try:
            user_input = input(f"{prompt_message}\n> ")
            user_input_clean = user_input.strip()
            user_input_lower = user_input_clean.lower()

            if not user_input_clean or user_input_lower == 'quit':
                print("Exiting conversation.")
                break

            # --- Process User Input/Feedback ---
            # Check for 'yes' only if there's history and it wasn't just a greeting
            if conversation_history and conversation_history[-1][1] != STANDARD_GREETING_RESPONSE and user_input_lower == 'yes':
                print("\nGreat! Attempting to extract relevant data as JSON...")
                last_query, last_answer = conversation_history[-1]
                summary_for_extraction = f"User asked: '{last_query}'\nAssistant answered: '{last_answer}'\nUser confirmed this was helpful."
                extracted_json = await extract_relevant_json(summary_for_extraction, deals_json_string)
                if extracted_json:
                    print("\n--- Extracted JSON Data ---")
                    try:
                        parsed_json = json.loads(extracted_json)
                        print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError:
                        LOGGER.warning("Extracted content was not valid JSON, printing raw.")
                        print(extracted_json)
                    print("--- End of JSON Data ---")
                else:
                    print("\nCould not extract specific JSON data based on the conversation.")
                break # Exit loop

            elif conversation_history and conversation_history[-1][1] != STANDARD_GREETING_RESPONSE and user_input_lower == 'no':
                 assistant_response = "Okay, I understand that wasn't quite right. Please tell me more specifically what you are looking for or how I can improve the answer."
                 print(f"\nAssistant:\n{assistant_response}")
                 conversation_history.append((user_input_clean, assistant_response)) # Log 'no' feedback
                 continue # Wait for user's next input (clarification)

            else:
                 # --- Prepare Prompt for RAG ---
                 # Treat input as a fresh query if it's the first turn OR if the previous turn was just the standard greeting
                 is_initial_query = not conversation_history
                 is_query_after_greeting = conversation_history and conversation_history[-1][1] == STANDARD_GREETING_RESPONSE

                 if is_initial_query or is_query_after_greeting:
                     current_llm_prompt = user_input_clean # Use the user's input directly
                     LOGGER.debug(f"Treating as new query for LLM: '{current_llm_prompt}'")
                 else: # It's a refinement after a real answer
                     prev_query, prev_answer = conversation_history[-1]
                     context = f"Previous query: '{prev_query}'\nMy previous answer: '{prev_answer}'\n"
                     current_llm_prompt = f"{context}User's follow-up/refinement: '{user_input_clean}'\nPlease provide an updated answer based *only* on the deals data and this new input."
                     LOGGER.debug(f"Treating as refinement for LLM. Full prompt starts with: {current_llm_prompt[:200]}...")

                 # --- Call RAG function ---
                 print("\nThinking...", file=sys.stderr)
                 answer = await answer_query(current_llm_prompt, deals_path) # answer_query handles internal greeting check

                 print("\nAssistant Answer:")
                 print("-" * 20)
                 formatted_answer = ""
                 for line in answer.splitlines():
                     print(line)
                     formatted_answer += line + "\n"
                 print("-" * 20)

                 # Store this turn
                 conversation_history.append((user_input_clean, formatted_answer.strip()))


        except EOFError:
            print("\nInput stream closed. Exiting.")
            break
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            break
        except Exception as e:
            LOGGER.exception("An error occurred during the main conversation loop:")
            print(f"\nAn error occurred: {e}", file=sys.stderr)
            print("Please check the logs for more details.", file=sys.stderr)
            break

    # --- End of Loop ---
    if iteration >= max_iterations:
        print("\nMaximum conversation turns reached. Exiting.")
    else:
        # Message already printed if user quit or said 'yes'
        pass # print("\nConversation finished.")


if __name__ == "__main__":
    # --- UTF-8 Configuration ---
    required_encoding = 'utf-8'
    try:
        for stream in [sys.stdin, sys.stdout, sys.stderr]:
            if hasattr(stream, 'reconfigure') and (getattr(stream, 'encoding', None) is None or stream.encoding.lower() != required_encoding):
                try:
                     stream.reconfigure(encoding=required_encoding)
                except Exception as reconfig_err:
                     LOGGER.warning(f"Could not reconfigure {getattr(stream, 'name', 'stream')} for UTF-8: {reconfig_err}")
    except Exception as e:
        LOGGER.error(f"Error setting up standard streams: {e}")

    # --- Run Main Async Function ---
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        LOGGER.exception("An unexpected error occurred at the top level:")
        print(f"\nA critical error occurred: {e}", file=sys.stderr)
        sys.exit(1)