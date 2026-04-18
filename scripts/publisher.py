#!/usr/bin/env python3
"""
AITechNews Publisher (Gemini/Groq + Hugging Face Stable Diffusion)
Generates Devnagri + English articles and uploads high-quality HF images directly to aitechindia.
Includes automated posting to Twitter and Telegram channels.
"""

import os
import json
import feedparser
import requests
import re
import time
import base64
from datetime import datetime, timezone
from typing import Optional

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# =============================================================================
# CONFIGURATION
# =============================================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.environ.get("AITECHINDIA_TOKEN", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Social Media
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")

GITHUB_REPO = "Yoginogia/aitechindia"
CONTENT_PATH = "src/content/blog"
IMAGE_PATH = "public/images/blog"

if GEMINI_API_KEY and HAS_GEMINI:
    genai.configure(api_key=GEMINI_API_KEY)

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/ai/feed/",
    "https://blog.google/technology/ai/rss/",
    "https://openai.com/blog/rss.xml",
    "https://gadgets.ndtv.com/rss/feeds",
    "https://analyticsindiamag.com/feed/",
    "https://www.91mobiles.com/hub/feed/",
]

def fetch_news() -> list[dict]:
    news = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title = entry.get("title", "").strip()
                summary_raw = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r'<[^>]+>', '', summary_raw).strip()[:400]
                if title and len(title) > 20:
                    news.append({
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", "")
                    })
        except Exception as e:
            print(f"  ✗ Error fetching {url}: {e}")
    return news

def parse_json_response(response_text: str) -> Optional[dict]:
    try:
        clean = re.sub(r'```json|```', '', response_text).strip()
        start_idx = clean.find('{')
        end_idx = clean.rfind('}') + 1
        return json.loads(clean[start_idx:end_idx])
    except Exception:
        return None

def call_ai(prompt: str) -> str:
    if GEMINI_API_KEY and HAS_GEMINI:
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"  [Gemini failed, trying Groq...] {e}")
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.75
        },
        timeout=60
    )
    return response.json()["choices"][0]["message"]["content"]

def generate_and_upload_hf_image(title: str, slug: str) -> str:
    if not HF_TOKEN:
        print("  ✗ HF_TOKEN missing! Falling back to pollinations.")
        encoded = title.replace(" ", "%20")
        return f"https://image.pollinations.ai/prompt/hyperrealistic%20high-tech%20{encoded}?width=800&height=450&nologo=true"
    
    print("  Generating HF Image via SDXL...")
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    prompt = f"hyperrealistic, extremely detailed, cinematic lighting, futuristic technology, 8k resolution, masterpiece, glowing neon aesthetics, photorealistic: {title}"
    
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    if response.status_code != 200 or len(response.content) < 1000:
        print("  ✗ HF Image generation failed, falling back to Pollinations.")
        encoded = title.replace(" ", "%20")
        return f"https://image.pollinations.ai/prompt/hyperrealistic%20high-tech%20{encoded}?width=800&height=450&nologo=true"
    
    image_filename = f"{slug}.jpg"
    upload_success = push_file_to_github(f"{IMAGE_PATH}/{image_filename}", response.content, is_binary=True)
    
    if upload_success:
        print(f"  ✓ High-quality image uploaded to {IMAGE_PATH}/{image_filename}")
        return f"/images/blog/{image_filename}"
    else:
        print(f"  ✗ Failed to upload image to Github. Falling back to pollinations.")
        return f"https://image.pollinations.ai/prompt/hyperrealistic%20high-tech%20{title.replace(' ', '%20')}?width=800&height=450&nologo=true"

def push_file_to_github(filepath: str, content, is_binary: bool = False) -> bool:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    sha = None
    check_response = requests.get(url, headers=headers)
    if check_response.status_code == 200:
        sha = check_response.json().get("sha")

    if is_binary:
        encoded_content = base64.b64encode(content).decode('ascii')
    else:
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('ascii')

    payload = {
        "message": f"Auto: Create/Update {filepath.split('/')[-1]}",
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(url, headers=headers, json=payload)
    return put_response.status_code in [200, 201]

def post_to_telegram(title: str, slug: str, image_url: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [Telegram] Skipping: Credentials not set.")
        return
    article_url = f"https://aitechnews.co.in/blog/{slug}"
    # Assuming the channel ID was provided directly, but usually requires @ handle for public channels.
    chat_id = TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID.startswith('@') or TELEGRAM_CHAT_ID.startswith('-') else f"@{TELEGRAM_CHAT_ID}"
    
    caption = f"🚨 *New Article Released!*\n\n{title}\n\n👉 [Read Full Article Here]({article_url})\n\n#AINews #Technology"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    photo_url = f"https://aitechnews.co.in{image_url}" if image_url.startswith("/") else image_url

    try:
        res = requests.post(url, json={
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "Markdown"
        })
        if res.status_code == 200:
            print("  ✓ Posted to Telegram")
        else:
            print(f"  ✗ Telegram API error: {res.text}")
    except Exception as e:
        print(f"  ✗ Failed to post to Telegram: {e}")

def post_to_twitter(title: str, slug: str):
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("  [Twitter] Skipping: Credentials not set.")
        return
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY, consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET
        )
        article_url = f"https://aitechnews.co.in/blog/{slug}"
        text = f"🔥 {title}\n\nRead the full story: {article_url}\n#AINews #Tech #India"
        client.create_tweet(text=text)
        print("  ✓ Posted to Twitter")
    except Exception as e:
        print(f"  ✗ Failed to post to Twitter: {e}")

def generate_article(item: dict) -> Optional[dict]:
    prompt = f"""You are AITechIndia's expert Hinglish writer. Write a 500-word engaging tech article.

News Topic: "{item['title']}"
Context: {item['summary']}

CRITICAL RULES:
1. MUST MIX Devanagari (हिंदी) and English naturally. Do NOT use only english letters for Hindi! 
2. Example of required language style: "Apple ने एक नया iPhone launch किया है, जो industry में game changer साबित हो सकता है।" 
3. Both Headings (##) and text MUST be a mix of English and Devanagari Hindi. 
4. Headings must have Emojis (🔥⚡🚀💡🤖📱)
5. Add an India-specific perspective where possible.

Respond ONLY with valid JSON (no markdown formatting, no backticks, just raw JSON text):
{{"title":"Catchy Title with emoji (Mix of Hindi in Devnagari & English) under 80 chars","slug":"url-friendly-slug-with-only-english-letters","excerpt":"2-3 line preview (Mix Hindi/Devnagari + English)","content":"Full article text (Mix Hindi/Devnagari + English). Use \\n\\n for paragraphs","category":"AI","readingTime":"4 min read"}}"""
    try:
        response = call_ai(prompt)
        return parse_json_response(response)
    except Exception as e:
        print(f"  ✗ Text Generation error: {e}")
        return None

def create_markdown(article: dict, today_formatted: str, image_url: str) -> str:
    title = article['title'].replace('"', "'")
    excerpt = article['excerpt'].replace('"', "'")
    category = article.get('category', 'AI')
    reading_time = article.get('readingTime', '4 min read')

    return f"""---
title: "{title}"
date: "{today_formatted}"
category: "{category}"
excerpt: "{excerpt}"
image: "{image_url}"
readingTime: "{reading_time}"
---

{article['content']}
"""

def main():
    print("=" * 60)
    print("=== AITechNews Publisher (Social Media Integration) ===")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
    print("=" * 60)

    news = fetch_news()
    if not news:
        print("No news found!")
        return

    today_formatted = datetime.now(timezone.utc).strftime("%d %B %Y")
    today_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    article_count = int(os.environ.get("ARTICLES_COUNT", "3"))
    published_count = 0

    selected = news[::max(1, len(news) // article_count)][:article_count]

    for i, item in enumerate(selected):
        print(f"\n📝 Writing article {i + 1}/{article_count}: {item['title'][:55]}...")
        try:
            article = generate_article(item)
            if not article:
                print("  ✗ Skipping - generation failed")
                continue

            slug = re.sub(r'[^a-z0-9-]', '', article.get("slug", "ai-news").lower())[:50]
            filename = f"{slug}-{today_slug}.md"
            
            clean_title = re.sub(r'[^\w\s-]', '', item['title'])
            image_url = generate_and_upload_hf_image(clean_title, slug)

            md_content = create_markdown(article, today_formatted, image_url)
            if push_file_to_github(f"{CONTENT_PATH}/{filename}", md_content, is_binary=False):
                published_count += 1
                print(f"  ✓ Markdown {filename} pushed to repo.")
                
                # Push to Social Media
                post_to_telegram(article['title'], filename.replace('.md',''), image_url)
                post_to_twitter(article['title'], filename.replace('.md',''))

            time.sleep(5)

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n{'='*60}")
    print(f"✅ Done! {published_count}/{article_count} articles published!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
