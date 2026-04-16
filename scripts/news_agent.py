#!/usr/bin/env python3
"""
AITechNews - Final Agent
Directly pushes .md files to aitechindia repo via GitHub API
"""

import os
import json
import feedparser
import requests
from datetime import datetime, timezone
import re
import time
import base64
from typing import Optional


# =============================================================================
# CONFIGURATION
# =============================================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

GITHUB_TOKEN = os.environ.get("AITECHINDIA_TOKEN", "")
GITHUB_REPO = "Yoginogia/aitechindia"
CONTENT_PATH = "src/content/blog"

ARTICLES_TO_WRITE = int(os.environ.get("ARTICLES_COUNT", "3"))

UNSPLASH_IMAGES = [
    "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=800&q=80",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&q=80",
    "https://images.unsplash.com/photo-1655720828018-edd2daec9349?w=800&q=80",
    "https://images.unsplash.com/photo-1676573394842-08f9f41ff84a?w=800&q=80",
    "https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=800&q=80",
]

RSS_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/ai/feed/"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "ArsTechnica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Analytics India Mag", "url": "https://analyticsindiamag.com/feed/"},
]


def fetch_news() -> list[dict]:
    """Fetch news articles from configured RSS feeds."""
    print("Fetching news from RSS feeds...")
    all_articles = []
    
    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                summary_raw = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r'<[^>]+>', '', summary_raw).strip()[:400]
                
                if title and len(title) > 20:
                    all_articles.append({
                        "source": feed_info["name"],
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", "")
                    })
            print(f"  ✓ {feed_info['name']}: fetched")
        except Exception as e:
            print(f"  ✗ {feed_info['name']}: {e}")
    
    print(f"Total: {len(all_articles)} articles")
    return all_articles


def call_groq(prompt: str, max_tokens: int = 1000) -> str:
    """Make API call to Groq for text generation."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is missing!")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    
    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"Groq API error {response.status_code}: {response.text[:200]}")
    
    return response.json()["choices"][0]["message"]["content"]


def parse_json_response(response_text: str, start_char: str = '{', end_char: str = '}') -> Optional[dict | list]:
    """Extract and parse JSON from response text."""
    try:
        clean = re.sub(r'```json|```', '', response_text).strip()
        start_idx = clean.find(start_char)
        end_idx = clean.rfind(end_char) + 1
        
        if start_idx == -1 or end_idx == 0:
            return None
            
        return json.loads(clean[start_idx:end_idx])
    except Exception:
        return None


def choose_topics(articles: list[dict], count: int = 3) -> list[dict]:
    """Select top topics from fetched articles using Groq."""
    print(f"Selecting {count} topics with Groq...")
    
    articles_text = "\n".join([
        f"{i+1}. [{a['source']}] {a['title']}" 
        for i, a in enumerate(articles[:20])
    ])
    
    prompt = f"""Select TOP {count} most interesting AI/tech stories for Indian audience from:

{articles_text}

Respond ONLY with valid JSON array:
[{{"index": 1, "title": "title", "category": "AI Tools", "hindi_angle": "Indian angle"}}]"""
    
    try:
        response = call_groq(prompt, max_tokens=500)
        topics = parse_json_response(response, '[', ']')
        
        if topics and isinstance(topics, list):
            print(f"  ✓ {len(topics)} topics selected!")
            return topics[:count]
    except Exception as e:
        print(f"  ✗ Topic selection error: {e}")
    
    # Fallback: return first N articles as topics
    return [
        {"index": i+1, "title": articles[i]["title"], "category": "Latest", "hindi_angle": "Tech update"} 
        for i in range(min(count, len(articles)))
    ]


def write_article(topic: dict, source: dict) -> Optional[dict]:
    """Generate article content using Groq."""
    print(f"Writing article: {topic['title'][:50]}...")
    
    prompt = f"""Write a 450-word Hinglish tech article for AITechNews.co.in about:
Topic: {topic['title']}
Indian angle: {topic.get('hindi_angle', '')}
Summary: {source.get('summary', '')}

Use Hindi+English mix naturally. Use ## for headings, **bold** for key terms.

Respond ONLY with JSON (no backticks):
{{"title": "Hinglish title under 80 chars", "slug": "url-slug-2026", "excerpt": "2-3 line preview", "content": "full article with \\n\\n paragraphs", "readingTime": "4 min read", "tags": ["AI", "tag2"]}}"""
    
    try:
        response = call_groq(prompt, max_tokens=1800)
        article = parse_json_response(response)
        
        if article:
            print(f"  ✓ Ready: {article.get('title', '')[:45]}")
            return article
    except Exception as e:
        print(f"  ✗ Write error: {e}")
    
    return None

def push_md_to_github(article: dict, topic: dict, source: dict, image_url: str) -> bool:
    """Push markdown article to GitHub repository."""
    if not GITHUB_TOKEN:
        print("  ✗ ERROR: AITECHINDIA_TOKEN missing!")
        return False

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = re.sub(r'[^a-z0-9-]', '', article.get("slug", "ai-news").lower())[:55]
    filename = f"{slug}-{today}.md"

    md_content = f"""---
title: "{article['title'].replace('"', "'")}"
date: {today}
category: {topic.get('category', 'Latest')}
excerpt: "{article['excerpt'].replace('"', "'")}"
image: {image_url}
readingTime: {article.get('readingTime', '4 min read')}
tags: {json.dumps(article.get('tags', ['AI', 'Tech']))}
---

{article['content']}
"""

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CONTENT_PATH}/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Check if file exists
    sha = None
    check_response = requests.get(url, headers=headers)
    if check_response.status_code == 200:
        sha = check_response.json().get("sha")

    payload = {
        "message": f"Auto article: {article['title'][:50]} - {today}",
        "content": base64.b64encode(md_content.encode("utf-8")).decode("utf-8"),
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(url, headers=headers, json=payload)
    
    if put_response.status_code in [200, 201]:
        print(f"  ✓ PUSHED to aitechindia: {CONTENT_PATH}/{filename}")
        return True
    else:
        print(f"  ✗ PUSH FAILED {put_response.status_code}: {put_response.text[:300]}")
        return False


def main():
    """Main entry point for the news agent."""
    print("=" * 55)
    print("AITechNews Agent - Pushing to aitechindia repo!")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    all_news = fetch_news()
    if not all_news:
        print("No news found!")
        return

    topics = choose_topics(all_news, count=ARTICLES_TO_WRITE)
    print(f"\n{len(topics)} articles to write...")
    
    published = []

    for i, topic in enumerate(topics):
        idx = max(0, min(topic.get("index", i + 1) - 1, len(all_news) - 1))
        source = all_news[idx]
        
        article = write_article(topic, source)
        if not article:
            continue
        
        image_url = UNSPLASH_IMAGES[i % len(UNSPLASH_IMAGES)]
        success = push_md_to_github(article, topic, source, image_url)
        
        if success:
            published.append(article['title'])
        
        time.sleep(4)

    print("\n" + "=" * 55)
    print(f"DONE! {len(published)} articles pushed to aitechindia repo!")
    for title in published:
        print(f"  - {title[:60]}")
    print("Vercel auto-deploy -> aitechnews.co.in pe LIVE!")
    print("=" * 55)


if __name__ == "__main__":
    main()
