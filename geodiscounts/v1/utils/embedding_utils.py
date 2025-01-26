from typing import List

import torch
from transformers import AutoModel, AutoTokenizer

# Initialize model and tokenizer (use a pre-trained embedding model)
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")


def generate_embedding(query: str) -> List[float]:
    """
    Generate an embedding vector for the given query string.

    Args:
        query (str): The input query string.

    Returns:
        List[float]: The embedding vector as a list of floats.
    """
    try:
        inputs = tokenizer(query, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()
        return embedding
    except Exception as e:
        raise ValueError(f"Failed to generate embedding: {str(e)}")
