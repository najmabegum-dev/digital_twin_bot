"""
bot.py

The Telegram bot itself. When a friend messages it:
  1. Embeds their message
  2. Finds the most similar past (input, reply) pairs from your real chats
  3. Builds a prompt with those examples as few-shot context
  4. Sends it to Ollama Cloud (the AI model runs on Ollama's servers, not
     your laptop -- good since 4GB RAM can't run a good local model)
  5. Replies in your voice

Free tier of Ollama Cloud is used here. Embeddings (retrieval) still run
locally on your machine since that part is light enough for 4GB RAM.

SETUP:
    1. pip install python-telegram-bot sentence-transformers numpy ollama python-dotenv
    2. Sign up free at https://ollama.com (no card needed)
    3. Create an API key at https://ollama.com/settings/keys
    4. Create a .env file in this folder (gitignored, stays off GitHub):
           BOT_TOKEN=your_telegram_token_here
           OLLAMA_API_KEY=your_ollama_key_here
    5. Run parse_chats.py then build_index.py first.
    6. Run: python bot.py
"""

import os
import json
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from ollama import Client
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# Load keys from .env file -- never commit .env to GitHub
load_dotenv()

# ===== CONFIG =====
# Keys come from your .env file. Do NOT paste real tokens here directly.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")

# Pick a model from https://ollama.com/cloud -- stick to lighter ones
# to stay comfortably within the free tier quota.
OLLAMA_MODEL = "llama3.1:8b-cloud"

YOUR_NAME = "Najma"
NUM_EXAMPLES = 6               # how many past replies to use as style reference
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# Client pointed at Ollama's cloud servers instead of localhost
ollama_client = Client(
    host="https://ollama.com",
    headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
)

META_FILE = "pairs_meta.json"
INDEX_FILE = "embeddings.npy"
HISTORY_FILE = "chat_history.jsonl"

# ===== LOAD DATA AND MODELS (once, at startup) =====
print("Loading embedding model...")
embed_model = SentenceTransformer(EMBED_MODEL_NAME)

print("Loading your chat pairs and embeddings...")
with open(META_FILE, "r", encoding="utf-8") as f:
    pairs = json.load(f)
embeddings = np.load(INDEX_FILE)

print(f"Ready. Loaded {len(pairs)} reference pairs.")


def get_similar_examples(message, top_k=NUM_EXAMPLES):
    """Find the most similar past (input, reply) pairs to the incoming message."""
    query_emb = embed_model.encode([message], normalize_embeddings=True)[0]
    scores = embeddings @ query_emb  # cosine similarity (vectors are normalized)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [pairs[i] for i in top_indices]


def build_prompt(message, examples):
    """Construct the few-shot prompt for the local LLM."""
    example_block = "\n\n".join(
        f'Someone said: "{ex["input"]}"\n{YOUR_NAME} replied: "{ex["reply"]}"'
        for ex in examples
    )

    system_prompt = f"""You are texting as {YOUR_NAME}. Below are real examples of how
{YOUR_NAME} replies to messages, showing their tone, slang, length, and personality.
Study these closely and reply to the new message in exactly the same voice.
Keep replies short and casual, the way real texting is. Do not explain that
you are an AI. Just reply as {YOUR_NAME} would.

EXAMPLES:
{example_block}

Now reply to this new message in {YOUR_NAME}'s voice. Reply with ONLY the
message text, nothing else.

New message: "{message}"
{YOUR_NAME}'s reply:"""

    return system_prompt


def log_message(chat_id, sender_name, incoming_text, reply_text):
    """Append this exchange to a local .jsonl history file -- one JSON object per line."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "chat_id": chat_id,
        "from": sender_name,
        "incoming": incoming_text,
        "reply": reply_text,
    }
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    examples = get_similar_examples(user_message)
    prompt = build_prompt(user_message, examples)

    response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    reply_text = response["message"]["content"].strip()

    # Strip stray quotes the model sometimes adds
    if reply_text.startswith('"') and reply_text.endswith('"'):
        reply_text = reply_text[1:-1]

    log_message(
        chat_id=update.message.chat_id,
        sender_name=update.message.from_user.first_name,
        incoming_text=user_message,
        reply_text=reply_text,
    )

    await update.message.reply_text(reply_text)


def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found. Add it to your .env file.")
        print("  Create a file called .env in this folder with:")
        print("  BOT_TOKEN=your_telegram_token_here")
        return

    if not OLLAMA_API_KEY:
        print("ERROR: OLLAMA_API_KEY not found. Add it to your .env file.")
        print("  Add this line to your .env file:")
        print("  OLLAMA_API_KEY=your_ollama_key_here")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running. Go talk to it on Telegram!")
    app.run_polling()


if __name__ == "__main__":
    main()