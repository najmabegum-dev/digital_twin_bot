"""
build_index.py

Takes pairs.json (from parse_chats.py) and builds a local embeddings index
so the bot can retrieve your most similar past replies for any new message.

This step always runs locally and is free either way -- it's light enough
for 4GB RAM. Only the actual reply-generation (in bot.py) uses Ollama Cloud.
Uses sentence-transformers, no API calls, no account needed for this part.

USAGE:
    python build_index.py
"""

import json
import numpy as np
from sentence_transformers import SentenceTransformer

PAIRS_FILE = "pairs.json"
INDEX_FILE = "embeddings.npy"
META_FILE = "pairs_meta.json"

MODEL_NAME = "all-MiniLM-L6-v2"  # small, fast, free, runs on CPU


def main():
    with open(PAIRS_FILE, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    if not pairs:
        print("pairs.json is empty. Run parse_chats.py first.")
        return

    print(f"Loaded {len(pairs)} pairs. Loading embedding model (first run downloads ~80MB)...")
    model = SentenceTransformer(MODEL_NAME)

    inputs = [p["input"] for p in pairs]
    print("Embedding messages...")
    embeddings = model.encode(inputs, show_progress_bar=True, normalize_embeddings=True)

    np.save(INDEX_FILE, embeddings)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(pairs, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(pairs)} embeddings to {INDEX_FILE}")
    print(f"Saved matching pairs to {META_FILE}")
    print("\nDone. You can now run the bot with: python bot.py")


if __name__ == "__main__":
    main()