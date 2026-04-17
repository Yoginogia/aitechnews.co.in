#!/usr/bin/env python3
"""
AITechNews Publisher
Simplified version for publishing AI-generated articles to GitHub
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


# =============================================================================
# CONFIGURATION
# =============================================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GITHUB_TOKEN = os.environ.get("AITECHINDIA_TOKEN", "")
GITHUB_REPO = "Yoginogia/aitechnews.co.in"
CONTENT_PATH = "articles"

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/ai/feed/",
    "https://blog.google/technology/ai/rss/",
    "https://openai.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
]

UNSPLASH_IMAGES = [
    "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=800&q=80",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&q=80",
    "https://images.unsplash.com/photo-1655720828018-edd2daec9349?w=800&q=80",
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
                summary = re.sub(r'<[^>]+>', '', summary_raw).strip()[:300]
                
                if title and len(title) > 20:
                    news.append({
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", "")
                    })
        except Exception as e:
            print(f"  ✗ Error fetching {url}: {e}")
    
    print(f"Fetched: {len(news)} articles")
    return news


def call_groq(prompt: str, max_tokens: int = 1000) -> Optional[str]:
    """Make API call to Groq for text generation."""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            },
            timeout=60
        )
        
        response_data = response.json()
        
        # Check for API errors
        if response.status_code != 200:
            print(f"  ✗ API Error ({response.status_code}): {response_data.get('error', {}).get('message', 'Unknown error')}")
            return None
        
        # Extract content safely
        choices = response_data.get("choices", [])
        if not choices:
            print("  ✗ No choices in API response")
            return None
            
        content = choices[0].get("message", {}).get("content")
        if not content:
            print("  ✗ No content in API response")
            return None
            
        return content
        
    except requests.exceptions.Timeout:
        print("  ✗ API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request error: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return None


def parse_json_response(response_text: str) -> Optional[dict]:
    """Extract and parse JSON from response text."""
    try:
        clean = re.sub(r'```json|```', '', response_text).strip()
        start_idx = clean.find('{')
        end_idx = clean.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            return None
            
        return json.loads(clean[start_idx:end_idx])
    except Exception:
        return None


def push_to_github(filename: str, content: str) -> bool:
    """Push markdown file to GitHub repository."""
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
        "message": f"Auto: {filename}",
        "content": base64.b64encode(content.encode()).decode(),
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
    """Generate article content using Groq."""
    prompt = f"""Write a 400-word Hinglish tech article for AITechNews.co.in about:
"{item['title']}"
Summary: {item['summary']}

Respond ONLY with JSON (no backticks):
{{"title":"Hinglish title","slug":"url-slug","excerpt":"2 line preview","content":"full article with \\n\\n paragraphs","category":"AI News","readingTime":"3 min read"}}"""
    
    try:
        response = call_groq(prompt, max_tokens=1500)
        return parse_json_response(response)
    except Exception as e:
        print(f"  ✗ Generation error: {e}")
        return None


def create_markdown(article: dict, today: str, image_url: str) -> str:
    """Create markdown content with frontmatter."""
    return f"""---
title: "{article['title'].replace('"', "'")}"
date: {today}
category: {article.get('category', 'AI News')}
excerpt: "{article['excerpt'].replace('"', "'")}"
image: {image_url}
readingTime: {article.get('readingTime', '3 min read')}
---

{article['content']}
"""


def main():
    """Main entry point for the publisher."""
    print("=== AITechNews Publisher ===")
    
    news = fetch_news()
    if not news:
        print("No news found!")
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    article_count = int(os.environ.get("ARTICLES_COUNT", "3"))
    published_count = 0

    for i, item in enumerate(news[:article_count]):
        print(f"\nWriting article {i + 1}: {item['title'][:50]}")
        
        try:
            article = generate_article(item)
            if not article:
                continue
            
            slug = re.sub(r'[^a-z0-9-]', '', article.get("slug", "ai-news").lower())[:50]
            filename = f"{slug}-{today}.md"
            
            image_url = UNSPLASH_IMAGES[i % len(UNSPLASH_IMAGES)]
            md_content = create_markdown(article, today, image_url)
            
            if push_to_github(filename, md_content):
                published_count += 1
            
            time.sleep(4)
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n✓ Done! {published_count} articles published to aitechindia!")


if __name__ == "__main__":
    main()
