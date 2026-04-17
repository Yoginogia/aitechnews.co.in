#!/usr/bin/env python3
"""
AITechNews Publisher (Gemini AI + Pollinations AI Images)
Generates Devnagri + English articles using Gemini and AI images using Pollinations.
"""

import os
import json
import feedparser
import requests
import re
import time
import base64
import urllib.parse
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
GITHUB_REPO = "Yoginogia/aitechindia"
CONTENT_PATH = "src/content/blog"

if GEMINI_API_KEY and HAS_GEMINI:
    genai.configure(api_key=GEMINI_API_KEY)

RSS_FEEDS = [
    # Global AI & Tech
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/ai/feed/",
    "https://blog.google/technology/ai/rss/",
    "https://openai.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    # India Tech
    "https://gadgets.ndtv.com/rss/feeds",
    "https://analyticsindiamag.com/feed/",
    "https://www.91mobiles.com/hub/feed/",
]

def fetch_news() -> list[dict]:
    """Fetch news articles from RSS feeds."""
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
    print(f"Fetched: {len(news)} articles from RSS feeds")
    return news

def parse_json_response(response_text: str) -> Optional[dict]:
    """Extract and parse JSON from response text."""
    try:
        clean = re.sub(r'```json|```', '', response_text).strip()
        start_idx = clean.find('{')
        end_idx = clean.rfind('}') + 1
        return json.loads(clean[start_idx:end_idx])
    except Exception:
        return None

def call_ai(prompt: str) -> str:
    """Make API call to Gemini (primary) or Groq (fallback) for text generation."""
    if GEMINI_API_KEY and HAS_GEMINI:
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"  [Gemini failed, trying Groq...] {e}")
    
    # GROQ FALLBACK
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

def generate_ai_image_url(title: str) -> str:
    """Generate an AI image URL using pollinations.ai completely free."""
    # Create an image prompt based on the article title
    img_prompt = f"Futuristic technology illustration 8k resolution, cinematic lighting: {title}"
    encoded = urllib.parse.quote(img_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=450&nologo=true"

def push_to_github(filename: str, content: str) -> bool:
    """Push markdown file to GitHub repository."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CONTENT_PATH}/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    sha = None
    check_response = requests.get(url, headers=headers)
    if check_response.status_code == 200:
        sha = check_response.json().get("sha")
        print(f"  ℹ File already exists, updating...")

    payload = {
        "message": f"Auto: {filename}",
        "content": base64.b64encode(content.encode('utf-8')).decode(),
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(url, headers=headers, json=payload)
    success = put_response.status_code in [200, 201]
    status = "✓ PUSHED" if success else "✗ FAILED"
    print(f"  {status}: {filename} ({put_response.status_code})")
    return success

def generate_article(item: dict) -> Optional[dict]:
    """Generate Devnagri + English article content."""
    prompt = f"""You are AITechIndia's expert Hinglish writer. Write a 500-word engaging tech article.

News Topic: "{item['title']}"
Context: {item['summary']}

CRITICAL RULES:
1. MUST MIX Devanagari (हिंदी) and English naturally in the exact same sentence. DO NOT use only roman script! 
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
        print(f"  ✗ Generation error: {e}")
        return None

def create_markdown(article: dict, today_formatted: str, image_url: str) -> str:
    """Create markdown content with properly quoted frontmatter."""
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
    """Main entry point for the publisher."""
    print("=" * 55)
    print("=== AITechNews Publisher (Gemini AI Edition) ===")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
    print("=" * 55)

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
            
            # Use AI generated Image via Pollinations based on title
            image_url = generate_ai_image_url(article['title'])

            md_content = create_markdown(article, today_formatted, image_url)

            if push_to_github(filename, md_content):
                published_count += 1

            time.sleep(5)

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n{'='*55}")
    print(f"✅ Done! {published_count}/{article_count} articles published!")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
