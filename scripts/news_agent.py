#!/usr/bin/env python3
"""
AITechNews - Automated News Agent (Final Version)
Roz subah latest AI/Tech news fetch karke articles likhta hai
aur directly aitechindia repo mein .md files push karta hai!
"""

import os
import json
import feedparser
import requests
from datetime import datetime, timezone
from pathlib import Path
import re
import time
import base64

# ============================================================
# CONFIGURATION
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# aitechindia repo config
GITHUB_TOKEN = os.environ.get("AITECHINDIA_TOKEN", "")
GITHUB_REPO = "Yoginogia/aitechindia"
GITHUB_BRANCH = "main"
CONTENT_PATH = "src/content/blog"

ARTICLES_TO_WRITE = int(os.environ.get("ARTICLES_COUNT", "3"))

# Unsplash random image URLs by category
UNSPLASH_IMAGES = [
    "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=800&q=80",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&q=80",
    "https://images.unsplash.com/photo-1655720828018-edd2daec9349?w=800&q=80",
    "https://images.unsplash.com/photo-1676573394842-08f9f41ff84a?w=800&q=80",
    "https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=800&q=80",
    "https://images.unsplash.com/photo-1571171637578-41bc2dd41cd2?w=800&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80",
]

# ============================================================
# RSS FEEDS
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
# STEP 1: News Fetch
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

    print(f"\n📊 Total fetched: {len(all_articles)}")
    return all_articles

# ============================================================
# STEP 2: Topics Choose
# ============================================================
def choose_topics(articles, count=3):
    print(f"\n🤖 Groq se top {count} topics choose karwa raha hoon...")

    articles_text = "\n".join([
        f"{i+1}. [{a['source']}] {a['title']}\n   {a['summary'][:150]}"
        for i, a in enumerate(articles[:25])
    ])

    prompt = f"""You are an AI news editor for AITechNews.co.in, an Indian tech news website.

Here are today's latest AI and tech news headlines:

{articles_text}

Select the TOP {count} most interesting stories for Indian tech audience.
Focus on: AI breakthroughs, new tools, tech industry news, India-relevant tech.

Respond ONLY with valid JSON array, no markdown:
[
  {{
    "index": <number from list>,
    "title": "<original title>",
    "category": "<one of: AI Tools, Gadgets, Software Updates, Crypto, Latest>",
    "hindi_angle": "<Indian angle for this story in one line>"
  }}
]"""

    try:
        response = call_groq(prompt, max_tokens=600)
        clean = re.sub(r'```json|```', '', response).strip()
        start = clean.find('[')
        end = clean.rfind(']') + 1
        topics = json.loads(clean[start:end])
        print(f"  ✅ {len(topics)} topics selected!")
        return topics[:count]
    except Exception as e:
        print(f"  ❌ Topic selection error: {e}")
        return [{"index": i+1, "title": articles[i]["title"], "category": "Latest", "hindi_angle": "Tech update"} for i in range(min(count, len(articles)))]

# ============================================================
# STEP 3: Article Likho
# ============================================================
def write_article(topic, article_data):
    print(f"\n✍️  Article: {topic['title'][:55]}...")

    prompt = f"""You are a professional tech journalist for AITechNews.co.in, an Indian AI news website.

Write a news article in Hinglish (Hindi + English mix) about:
Topic: {topic['title']}
Indian Angle: {topic.get('hindi_angle', '')}
Summary: {article_data.get('summary', '')}

Requirements:
- Length: 450-550 words
- Language: Hinglish (natural Hindi+English mix, use Devanagari script for Hindi words)
- Structure: Hook intro → Main story → India impact → Expert view → Conclusion
- Use ## for section headings, **bold** for key terms
- Tone: Friendly, informative

Respond ONLY with valid JSON (no markdown backticks):
{{
  "title": "Catchy Hinglish title (under 80 chars)",
  "slug": "lowercase-url-slug-with-hyphens-2026",
  "excerpt": "2-3 line preview in Hinglish",
  "content": "Full article content with ## headings and **bold**. Use \\n\\n for paragraphs.",
  "readingTime": "4 min read",
  "tags": ["AI", "tag2", "tag3"]
}}"""

    try:
        response = call_groq(prompt, max_tokens=1800)
        clean = re.sub(r'```json|```', '', response).strip()
        start = clean.find('{')
        end = clean.rfind('}') + 1
        article = json.loads(clean[start:end])
        print(f"  ✅ Ready: {article.get('title', '')[:50]}")
        return article
    except Exception as e:
        print(f"  ❌ Writing error: {e}")
        return None

# ============================================================
# Groq API
# ============================================================
def call_groq(prompt, max_tokens=1000):
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY missing!")

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
        raise Exception(f"Groq error {response.status_code}: {response.text[:200]}")
    return response.json()["choices"][0]["message"]["content"]

# ============================================================
# STEP 4: MD File banao
# ============================================================
def create_md_content(article, topic, source_info, image_url):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    category = topic.get("category", "Latest")
    
    frontmatter = f"""---
title: "{article['title'].replace('"', "'")}"
date: {today}
category: {category}
excerpt: "{article['excerpt'].replace('"', "'")}"
image: {image_url}
readingTime: {article.get('readingTime', '4 min read')}
tags: {json.dumps(article.get('tags', ['AI', 'Tech']))}
source: "{source_info.get('source', 'AI News')}"
sourceUrl: "{source_info.get('link', '')}"
---

{article['content']}
"""
    return frontmatter

# ============================================================
# STEP 5: GitHub pe Push karo
# ============================================================
def push_to_github(filename, content, commit_message):
    if not GITHUB_TOKEN:
        raise ValueError("AITECHINDIA_TOKEN missing!")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CONTENT_PATH}/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Check if file exists (for update)
    sha = None
    check = requests.get(url, headers=headers)
    if check.status_code == 200:
        sha = check.json().get("sha")

    # File content encode karo
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": commit_message,
        "content": encoded,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        print(f"  🚀 GitHub pe push: {filename}")
        return True
    else:
        print(f"  ❌ Push failed: {response.status_code} - {response.text[:200]}")
        return False

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("🚀 AITechNews Agent — aitechindia repo pe publish!")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')} IST")
    print("=" * 60)

    # News fetch
    all_news = fetch_news()
    if not all_news:
        print("❌ Koi news nahi mili!")
        return

    # Topics choose
    selected_topics = choose_topics(all_news, count=ARTICLES_TO_WRITE)

    # Articles likho aur push karo
    print(f"\n📝 {len(selected_topics)} articles likhna shuru...")
    published = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for i, topic in enumerate(selected_topics):
        idx = max(0, min(topic.get("index", i+1) - 1, len(all_news)-1))
        source = all_news[idx]

        # Article likho
        article = write_article(topic, source)
        if not article:
            continue

        # Slug aur filename
        slug = article.get("slug", f"ai-news-{i+1}")
        slug = re.sub(r'[^a-z0-9-]', '', slug.lower())[:60]
        filename = f"{slug}-{today}.md"

        # Image
        image_url = UNSPLASH_IMAGES[i % len(UNSPLASH_IMAGES)]

        # MD content banao
        md_content = create_md_content(article, topic, source, image_url)

        # GitHub pe push karo
        commit_msg = f"🤖 Auto article: {article['title'][:50]} - {today}"
        success = push_to_github(filename, md_content, commit_msg)

        if success:
            published.append(filename)

        time.sleep(4)  # Rate limit

    print("\n" + "=" * 60)
    print(f"✅ {len(published)} articles aitechindia repo pe publish!")
    for f in published:
        print(f"   📄 src/content/blog/{f}")
    print("=" * 60)
    print("🌐 Vercel auto-deploy → aitechnews.co.in pe live!")

if __name__ == "__main__":
    main()
