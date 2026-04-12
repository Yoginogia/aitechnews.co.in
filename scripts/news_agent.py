#!/usr/bin/env python3
"""
AITechNews - Automated News Agent (Groq Version - 100% FREE)
Roz subah latest AI/Tech news fetch karke articles likhta hai
Groq API use karta hai - Llama 3 model - bilkul free!
"""

import os
import json
import feedparser
import requests
from datetime import datetime, timezone
from pathlib import Path
import re
import time

# ============================================================
# CONFIGURATION
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Best free model on Groq

ARTICLES_DIR = Path("articles")
ARTICLES_DIR.mkdir(exist_ok=True)

ARTICLES_TO_WRITE = int(os.environ.get("ARTICLES_COUNT", "3"))

# ============================================================
# RSS FEEDS — Latest AI & Tech News
# ============================================================
RSS_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/ai/feed/"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "ArsTechnica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Analytics India Mag", "url": "https://analyticsindiamag.com/feed/"},
]

# ============================================================
# STEP 1: RSS se News Fetch karo
# ============================================================
def fetch_news():
    print("📡 RSS feeds se news fetch kar raha hoon...")
    all_articles = []

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            count = 0
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                summary = re.sub(r'<[^>]+>', '', summary)[:500]
                link = entry.get("link", "")

                if title and len(title) > 20:
                    all_articles.append({
                        "source": feed_info["name"],
                        "title": title,
                        "summary": summary,
                        "link": link,
                    })
                    count += 1
            print(f"  ✅ {feed_info['name']}: {count} articles")
        except Exception as e:
            print(f"  ❌ {feed_info['name']} error: {e}")

    print(f"\n📊 Total articles fetched: {len(all_articles)}")
    return all_articles

# ============================================================
# STEP 2: Groq se Best Topics Choose karwao
# ============================================================
def choose_topics(articles, count=3):
    print(f"\n🤖 Groq (Llama 3) se top {count} topics choose karwa raha hoon...")

    articles_text = "\n".join([
        f"{i+1}. [{a['source']}] {a['title']}\n   {a['summary'][:150]}"
        for i, a in enumerate(articles[:25])
    ])

    prompt = f"""You are an AI news editor for AITechNews.co.in, an Indian tech news website.

Here are today's latest AI and tech news headlines:

{articles_text}

Select the TOP {count} most interesting and impactful stories for Indian tech audience.
Focus on: AI breakthroughs, new AI tools/products, tech industry news, India-relevant tech.

Respond ONLY with a valid JSON array, no markdown, no extra text:
[
  {{
    "index": <number from list above>,
    "title": "<article title>",
    "reason": "<why important for Indian audience>",
    "hindi_angle": "<unique Indian angle for this story>"
  }}
]"""

    try:
        response = call_groq(prompt, max_tokens=800)
        clean = re.sub(r'```json|```', '', response).strip()
        start = clean.find('[')
        end = clean.rfind(']') + 1
        if start >= 0 and end > start:
            clean = clean[start:end]
        topics = json.loads(clean)
        print(f"  ✅ {len(topics)} topics selected!")
        return topics[:count]
    except Exception as e:
        print(f"  ❌ Topic selection error: {e}")
        return [{"index": i+1, "title": articles[i]["title"], "reason": "Top news", "hindi_angle": "Tech update"} for i in range(min(count, len(articles)))]

# ============================================================
# STEP 3: Groq se Full Article Likhwao
# ============================================================
def write_article(topic, article_data):
    print(f"\n✍️  Article likh raha hoon: {topic['title'][:60]}...")

    prompt = f"""You are a professional tech journalist for AITechNews.co.in, an Indian AI news website.

Write a comprehensive news article in Hinglish (mix of Hindi and English) about:

Topic: {topic['title']}
Indian Angle: {topic.get('hindi_angle', 'Technology impact on India')}
Source Summary: {article_data.get('summary', '')}
Source: {article_data.get('source', 'Tech News')}

Requirements:
- Length: 400-500 words
- Language: Hinglish (Hindi + English tech terms mixed naturally)
- Structure: Catchy intro, Main story, India impact, Conclusion
- Tone: Friendly, informative, like talking to a tech-savvy friend

Respond ONLY with valid JSON, no markdown backticks:
{{
  "title": "Catchy Hinglish title under 70 chars",
  "slug": "url-friendly-slug-lowercase-with-hyphens",
  "excerpt": "2-3 line Hinglish summary for preview card",
  "content": "Full article here. Use \\n\\n for paragraph breaks.",
  "tags": ["tag1", "tag2", "tag3"],
  "category": "AI News",
  "readTime": "3 min read"
}}"""

    try:
        response = call_groq(prompt, max_tokens=1500)
        clean = re.sub(r'```json|```', '', response).strip()
        start = clean.find('{')
        end = clean.rfind('}') + 1
        if start >= 0 and end > start:
            clean = clean[start:end]
        article = json.loads(clean)
        print(f"  ✅ Article ready: {article.get('title', 'Unknown')[:50]}")
        return article
    except Exception as e:
        print(f"  ❌ Article writing error: {e}")
        return None

# ============================================================
# Groq API Call
# ============================================================
def call_groq(prompt, max_tokens=1000):
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable set nahi hai!")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)

    if response.status_code != 200:
        raise Exception(f"Groq API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    return data["choices"][0]["message"]["content"]

# ============================================================
# STEP 4: Articles Save karo
# ============================================================
def save_article(article, source_info):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = article.get("slug", "article").replace(" ", "-").lower()
    slug = re.sub(r'[^a-z0-9-]', '', slug)[:60]
    filename = f"{today}-{slug}.json"
    filepath = ARTICLES_DIR / filename

    full_article = {
        **article,
        "date": today,
        "publishedAt": datetime.now(timezone.utc).isoformat(),
        "source": source_info.get("source", "AI News"),
        "sourceUrl": source_info.get("link", ""),
        "featured": False,
        "views": 0,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(full_article, f, ensure_ascii=False, indent=2)

    print(f"  💾 Saved: {filename}")
    return filename

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("🚀 AITechNews AI Agent — Groq Edition (FREE!)")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} IST")
    print(f"🤖 Model: {GROQ_MODEL}")
    print("=" * 60)

    all_news = fetch_news()
    if not all_news:
        print("❌ Koi news nahi mili!")
        return

    selected_topics = choose_topics(all_news, count=ARTICLES_TO_WRITE)

    print(f"\n📝 {len(selected_topics)} articles likhna shuru...")
    written = []

    for i, topic in enumerate(selected_topics):
        idx = topic.get("index", i+1) - 1
        idx = max(0, min(idx, len(all_news)-1))
        source_article = all_news[idx]

        article = write_article(topic, source_article)
        if article:
            filename = save_article(article, source_article)
            written.append(filename)
            time.sleep(3)

    print("\n" + "=" * 60)
    print(f"✅ Done! {len(written)} articles successfully likhe:")
    for f in written:
        print(f"   📄 {f}")
    print("=" * 60)

if __name__ == "__main__":
    main()
