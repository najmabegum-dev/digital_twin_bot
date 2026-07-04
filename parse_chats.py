"""
parse_chats.py

Reads all WhatsApp .txt exports from the chats/ folder and turns them into
(their_message, your_reply) pairs, saved to pairs.json.

USAGE:
    1. Put your exported .txt files inside the chats/ folder.
    2. Edit YOUR_NAME below if needed (must match exactly how your name
       appears in the exports, e.g. "najma").
    3. Run: python parse_chats.py
"""

import os
import re
import json

YOUR_NAME = "✨"   # <-- change this if your name appears differently in exports
CHATS_FOLDER = "chats"
OUTPUT_FILE = "pairs.json"

# Matches lines like: "13/07/21, 1:04 pm - Big Ω: Assalamualikum"
# Also handles: "6/20/26, 14:32 - John: hey", "[6/20/26, 2:32:11 PM] John: hey"
# Date can be D/M/YY or M/D/YY (we don't care about the actual date value,
# only that this pattern marks the start of a new message).
LINE_PATTERN = re.compile(
    r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?\s?(?:[APap][Mm])?)\]?\s*-\s*([^:]+):\s(.*)$"
)


def parse_file(filepath):
    """Parse a single WhatsApp export file into a list of (sender, message) tuples."""
    messages = []
    current_sender = None
    current_text = None

    with open(filepath, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            match = LINE_PATTERN.match(line)

            if match:
                # New message line -- flush the previous one first
                if current_sender is not None:
                    messages.append((current_sender, current_text.strip()))

                _, _, sender, text = match.groups()
                current_sender = sender.strip()
                current_text = text
            else:
                # Continuation of a multi-line message
                if current_sender is not None and line.strip():
                    current_text += " " + line.strip()

        # flush last message
        if current_sender is not None:
            messages.append((current_sender, current_text.strip()))

    return messages


def filter_noise(text):
    """Skip system messages, media placeholders, deleted messages, etc."""
    noise_markers = [
        "<Media omitted>",
        "image omitted",
        "video omitted",
        "audio omitted",
        "sticker omitted",
        "This message was deleted",
        "Missed voice call",
        "Missed video call",
        "joined using this group",
        "changed the subject",
        "created group",
        "end-to-end encrypted",
    ]
    return any(marker.lower() in text.lower() for marker in noise_markers)


def build_pairs(messages):
    """
    Walk through chronological messages and whenever a friend's message
    is immediately followed by YOUR message, save it as a training pair.
    Consecutive messages from the same sender get merged into one block.
    """
    # Merge consecutive messages from the same sender
    merged = []
    for sender, text in messages:
        if filter_noise(text):
            continue
        if merged and merged[-1][0] == sender:
            merged[-1] = (sender, merged[-1][1] + " " + text)
        else:
            merged.append((sender, text))

    pairs = []
    for i in range(len(merged) - 1):
        sender_a, text_a = merged[i]
        sender_b, text_b = merged[i + 1]

        if sender_a.lower() != YOUR_NAME.lower() and sender_b.lower() == YOUR_NAME.lower():
            # friend's message -> your reply
            if len(text_a.strip()) > 0 and len(text_b.strip()) > 0:
                pairs.append({"input": text_a.strip(), "reply": text_b.strip()})

    return pairs


def main():
    if not os.path.isdir(CHATS_FOLDER):
        print(f"Folder '{CHATS_FOLDER}' not found. Create it and add your .txt exports.")
        return

    all_pairs = []
    files = [f for f in os.listdir(CHATS_FOLDER) if f.endswith(".txt")]

    if not files:
        print(f"No .txt files found in '{CHATS_FOLDER}'. Add your WhatsApp exports there.")
        return

    for filename in files:
        filepath = os.path.join(CHATS_FOLDER, filename)
        messages = parse_file(filepath)
        pairs = build_pairs(messages)
        print(f"{filename}: extracted {len(pairs)} pairs")
        all_pairs.extend(pairs)

    # Deduplicate identical pairs
    seen = set()
    unique_pairs = []
    for p in all_pairs:
        key = (p["input"], p["reply"])
        if key not in seen:
            seen.add(key)
            unique_pairs.append(p)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_pairs, f, indent=2, ensure_ascii=False)

    print(f"\nTotal unique pairs: {len(unique_pairs)}")
    print(f"Saved to {OUTPUT_FILE}")

    if len(unique_pairs) < 30:
        print("\nNote: you have fewer than 30 pairs. The bot will still work, but")
        print("more examples (50-100+) will make the style match much better.")


if __name__ == "__main__":
    main()