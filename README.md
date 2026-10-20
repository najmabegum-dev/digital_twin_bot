# Digital Twin Telegram Bot

A Telegram bot that replies the way I text. It learns from my exported WhatsApp chats using retrieval-augmented generation (RAG) and few-shot prompting. There is no fine-tuning, no GPU, and no paid API.

![Bot chatting on Telegram](docs/demo.png)

## How it works

1. WhatsApp chats are exported as `.txt` files and parsed into **(friend's message → my reply)** pairs.
2. Each pair is embedded locally with `sentence-transformers` (`all-MiniLM-L6-v2`), which is light enough to run on a 4 GB RAM laptop.
3. When someone messages the bot on Telegram, it embeds the new message and finds the 6 most similar past exchanges by cosine similarity.
4. Those exchanges go into a few-shot prompt, which is sent to a model on Ollama Cloud (free tier, `llama3.1:8b-cloud` by default).
5. The model answers in my voice, and the bot sends the reply back on Telegram.
6. Every exchange is appended to a local `chat_history.jsonl`.

```
WhatsApp .txt  →  parse_chats.py  →  build_index.py  →  embeddings.npy + pairs_meta.json
                                                                   │
Telegram message → bot.py → embed → top-6 similar replies → few-shot prompt → Ollama Cloud → reply
```

## Tech stack

Python · sentence-transformers · NumPy · Ollama Cloud · python-telegram-bot · python-dotenv

## Quick start

### 1. Get your keys

- **Ollama Cloud:** create a free account at https://ollama.com, then make an API key at https://ollama.com/settings/keys. You don't need to install Ollama locally or download any model files.
  > Free tier limits: session limits reset every 5 hours, weekly limits reset every 7 days, and you can run 1 cloud model at a time. That's plenty for a personal bot, and lighter models stretch the quota further.
- **Telegram:** open **@BotFather** in Telegram, send `/newbot`, pick a name and a username ending in `bot`, and copy the token it gives you.

### 2. Clone and install

```bash
git clone https://github.com/najmabegum-dev/digital_twin_bot.git
cd digital_twin_bot
pip install -r requirements.txt
```

### 3. Add your keys

Copy the example file and fill it in:

```bash
# Mac / Linux
cp .env.example .env

# Windows
copy .env.example .env
```

Then open `.env` and set:

```
BOT_TOKEN=your_telegram_token_here
OLLAMA_API_KEY=your_ollama_key_here
```

`.env` is gitignored, so your keys never get committed.

### 4. Export your chats

For each chat: open it in WhatsApp → tap the name → **Export Chat** → **Without Media**. Create a `chats/` folder and put the `.txt` files in it. Five or more chats gives better results.

### 5. Set your name

Open `parse_chats.py` and set `YOUR_NAME` to match how your name appears in the exports. Also update `YOUR_NAME` in `bot.py`, which is used in the prompt.

### 6. Build the data and run

```bash
python parse_chats.py     # creates pairs.json
python build_index.py     # creates embeddings.npy and pairs_meta.json (downloads a ~80 MB model the first time)
python bot.py             # starts the bot
```

When you see "Bot is running", message your bot on Telegram. Keep the terminal open while you want it active.

## Project structure

```
digital_twin_bot/
├── parse_chats.py      WhatsApp .txt → (message, reply) pairs
├── build_index.py      embeds the pairs and saves the index
├── bot.py              Telegram bot: retrieval, prompt building, reply
├── requirements.txt
├── .env.example        template for your keys
└── .gitignore          keeps chats, embeddings, history and keys out of git
```

## Tuning

- **Replies feel generic:** add more chats, or raise `NUM_EXAMPLES` in `bot.py` (try 8–10).
- **Hitting free-tier limits:** switch to a lighter model from https://ollama.com/cloud and update `OLLAMA_MODEL` in `bot.py` (the name must end in `-cloud`).
- **Want it to know facts about you:** add a short paragraph to the prompt in `build_prompt()` in `bot.py`.
- **Added more chats:** re-run `parse_chats.py` and `build_index.py`.
- **Occasional errors or slow replies:** Ollama Cloud is a newer service without a published uptime guarantee, so some flakiness is normal on the free tier. Retry, or check https://ollama.com/settings for quota status.

## Conversation history

Every exchange is appended to `chat_history.jsonl`, one JSON object per line, with a timestamp, the sender's name, their message and the bot's reply. The file is created the first time the bot replies, and it's gitignored because it contains real conversations.

To read it in Python:

```python
import json
with open("chat_history.jsonl") as f:
    history = [json.loads(line) for line in f]
```

## Privacy

- Chats, parsed pairs, embeddings and the conversation log stay on your machine. All of them are gitignored.
- For each reply, the new incoming message and the 6 retrieved examples are sent to Ollama Cloud. Check Ollama's current data policy yourself before using this with sensitive chats.
- Telegram relays the messages as it does for any bot.
- Your friends' messages are in your exports. Think about whether you're comfortable using them, and don't share the data files.

## Limitations

- Retrieval is based on semantic similarity of single messages, so the bot has no memory of earlier turns in a conversation.
- Quality depends on how many chats you give it and on the free-tier model.
- The bot runs only while your terminal is open, since it uses polling and isn't deployed anywhere.

## License

MIT. See [LICENSE](LICENSE).
