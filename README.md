# Digital Twin Telegram Bot

A Telegram bot that learns to text like you, trained on your real WhatsApp
chat history. No fine-tuning, no GPU, no paid API — built as a fun
learning project around retrieval-augmented generation (RAG) and few-shot
prompting.

**How it works, in short:** your past messages are embedded into vectors.
When a friend messages the bot, it finds your most similar past replies
and feeds them to an LLM as style examples, so the model replies the way
you actually would — same tone, same slang, same reply length.

**Stack:** Python · sentence-transformers (local embeddings) · Ollama Cloud
(free-tier LLM inference) · python-telegram-bot

---

## How it works
1. You export your WhatsApp chats as .txt files
2. A parser extracts every "friend's message -> your reply" pair
3. Those pairs get embedded (turned into searchable vectors) locally —
   this part is light and works fine on 4GB RAM
4. When someone messages the bot on Telegram, it finds your 6 most similar
   past replies and sends them as style examples to a model running on
   Ollama Cloud (free tier)
5. The LLM replies in your voice, and the bot sends it back on Telegram
6. Every exchange is logged locally to `chat_history.jsonl` so you have a
   running record of conversations the bot has had

---

## Step 1: Sign up for Ollama Cloud (free, no card needed)

1. Go to **https://ollama.com** and create a free account
2. Go to **https://ollama.com/settings/keys** and create an API key
3. Copy that key somewhere safe — you'll need it in Step 5

You do **not** need to install Ollama locally or download any model files.
Everything model-related happens on Ollama's servers.

> Free tier limits: session limits reset every 5 hours, weekly limits reset
> every 7 days, and you can run 1 cloud model at a time. That's plenty for
> a personal bot chatting with friends. Stick to lighter models (see Step 6)
> to stretch your quota further.

---

## Step 2: Export your WhatsApp chats

For each friend whose chats you want to learn from:
1. Open the chat in WhatsApp
2. Tap their name at the top → scroll down → **Export Chat**
3. Choose **Without Media**
4. Save/send yourself the resulting `.txt` file

Do this for 5+ chats to get a good variety of your replies. The more
messages, the better the bot will sound like you.

---

## Step 3: Set up the project folder

You should have these files (already created for you):
```
digital_twin/
├── chats/              <- put your exported .txt files in here (gitignored)
├── parse_chats.py
├── build_index.py
├── bot.py
├── requirements.txt
├── .gitignore
└── README.md (this file)
```

Put all your exported `.txt` files inside the `chats/` folder.

---

## Step 4: Install Python packages

```bash
pip install -r requirements.txt
```

---

## Step 5: Parse your chats

```bash
python parse_chats.py
```

This reads everything in `chats/` and creates `pairs.json` — a list of
(friend's message, your reply) pairs. It will print how many pairs it found.
If it's fewer than 30, consider exporting a few more chats for better results.

> Note: the script is already set to look for "najma" as your name. If your
> name appears differently in the exports (e.g. a nickname), open
> `parse_chats.py` and change the `YOUR_NAME` variable at the top.

---

## Step 6: Build the embeddings index

```bash
python build_index.py
```

First run will download a small (~80MB) embedding model — free, one-time,
and runs locally even on 4GB RAM. This creates `embeddings.npy` and
`pairs_meta.json`, used for retrieval.

---

## Step 7: Create your Telegram bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Give it a name and a username (must end in "bot", e.g. `najma_twin_bot`)
4. BotFather gives you a token like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`
5. Copy that token

---

## Step 8: Set your API keys and run the bot

Set your Ollama Cloud API key as an environment variable (recommended, so
it's not sitting in plain text in the code):

**Mac/Linux:**
```bash
export OLLAMA_API_KEY=your_key_here
```

**Windows (PowerShell):**
```powershell
setx OLLAMA_API_KEY "your_key_here"
```
(then close and reopen your terminal for it to take effect)

Then:
1. Open `bot.py`
2. Paste your Telegram token into the `BOT_TOKEN` variable near the top
3. Check `OLLAMA_MODEL` — it's set to `"llama3.1:8b-cloud"` by default,
   a good balance of quality and free-tier-friendliness. The `-cloud`
   suffix is what tells Ollama to run it on their servers, not yours.
4. Run it:
   ```bash
   python bot.py
   ```
5. You'll see "Bot is running." Now open Telegram, find your bot by its
   username, and send it a message — your friends can do the same.

Keep the terminal window open while you want the bot to be active — the
Python script and embeddings still run on your machine; only the actual
reply-generation happens on Ollama's cloud.

---

## Tuning tips

- **Replies too generic / not enough like you?** Export more chats, or
  increase `NUM_EXAMPLES` in `bot.py` (try 8-10) so it has more style
  reference per message.
- **Hitting free tier limits?** Try a smaller cloud model — check
  **https://ollama.com/cloud** for the current list and pick one on the
  lighter end, then update `OLLAMA_MODEL` in `bot.py` to match (must end
  in `-cloud`).
- **Want it to know facts about you** (job, hobbies, inside jokes)? Add a
  short paragraph of facts into the `system_prompt` in `bot.py`, right
  after the personality instructions.
- **Re-running after adding more chats**: just re-run `parse_chats.py` then
  `build_index.py` again — it'll rebuild from everything in `chats/`.
- **Occasional errors or slow replies**: Ollama Cloud is a newer service
  without a published uptime guarantee, so occasional flakiness is normal
  for a free-tier personal project like this. If it happens a lot, just
  retry, or check **https://ollama.com/settings** for quota status.

---

## Conversation history

Every exchange the bot has gets appended to `chat_history.jsonl` — one JSON
object per line, with timestamp, sender name, their message, and the bot's
reply. This file is created automatically the first time the bot replies
to someone. It's already excluded from git via `.gitignore` since it
contains real conversations.

To read it later in Python:
```python
import json
with open("chat_history.jsonl") as f:
    history = [json.loads(line) for line in f]
```

---

## Privacy note

Your chat data, the parser, and the embeddings stay on your own computer.
Only the new incoming message plus a handful of retrieved examples are sent
to Ollama Cloud to generate each reply. Per Ollama's policy, prompt and
response data sent to their cloud is not logged or used for training.
Nothing else is uploaded anywhere except what Telegram itself relays for
the bot to function (standard for all Telegram bots).