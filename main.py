import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

URL = "https://cryptorank.io/upcoming-ico"
SEEN_FILE = "seen_sales.json"

GOOD_WORDS = [
    "binance",
    "dao maker",
    "seedify",
    "polkastarter",
    "coinlist",
    "bybit",
    "gate",
    "ai",
    "zk",
    "defi",
    "gaming",
    "infra",
    "layer 2",
    "depin",
    "rwa"
]

BAD_WORDS = [
    "meme",
    "casino",
    "betting",
    "gambling"
]


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return []

    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen(seen_ids):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_ids, f, indent=2)


def get_page_html():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def looks_high_quality(sale):
    text = f"{sale.get('name', '')} {sale.get('type', '')} {sale.get('url', '')}".lower()

    has_good_word = any(word in text for word in GOOD_WORDS)
    has_bad_word = any(word in text for word in BAD_WORDS)

    return has_good_word and not has_bad_word


def extract_sales_from_html(html):
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)

    lines = text.split("\n")
    cleaned = [line.strip() for line in lines if line.strip()]

    results = []
    seen_names = set()

    for i, line in enumerate(cleaned):
        upper_line = line.upper()

        if upper_line in ["IDO", "ICO", "IEO"]:
            if i > 0:
                name = cleaned[i - 1]

                if name not in seen_names and len(name) > 1:
                    results.append({
                        "id": name,
                        "name": name,
                        "type": upper_line,
                        "date": "Check page",
                        "url": URL
                    })
                    seen_names.add(name)

    return results


def send_telegram_message(text):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }

    response = requests.post(telegram_url, json=payload, timeout=30)
    response.raise_for_status()


def main():
    print("STARTING SCRIPT")

    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN in .env")

    if not TELEGRAM_CHAT_ID:
        raise ValueError("Missing TELEGRAM_CHAT_ID in .env")

    seen_ids = load_seen()
    html = get_page_html()
    sales = extract_sales_from_html(html)

    print(f"Found {len(sales)} possible sales")

    new_sales = [sale for sale in sales if sale["id"] not in seen_ids]
    filtered_sales = [sale for sale in new_sales if looks_high_quality(sale)]

    if not filtered_sales:
        print("No high-quality sales found.")
        return

    for sale in filtered_sales[:10]:
        msg = (
            f"🚀 High-quality {sale['type']} found\n\n"
            f"Name: {sale['name']}\n"
            f"Date: {sale['date']}\n"
            f"Link: {sale['url']}"
        )
        send_telegram_message(msg)
        seen_ids.append(sale["id"])

    save_seen(seen_ids)
    print(f"Sent {len(filtered_sales[:10])} alerts.")


if __name__ == "__main__":
    main()
