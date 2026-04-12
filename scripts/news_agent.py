
#!/usr/bin/env python3
"""
AITechNews - Automated News Agent (Gemini Version - FREE)
Roz subah latest AI/Tech news fetch karke articles likhta hai
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

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
    {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/rss"},
    {"name": "ArsTechnica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
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
            for entry in feed.entries[:5]:  # Har feed se top 5
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                # HTML tags remove karo
                summary = re.sub(r'<[^>]+>', '', summary)[:500]
                link = entry.get("link", "")
                published = entry.get("published", str(datetime.now()))

                if title and len(title) > 20:
                    all_articles.append({
                        "source": feed_info["name"],
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "published": published
                    })
            print(f"  ✅ {feed_info['name']}: {len(feed.entries[:5])} articles")
        except Exception as e:
            print(f"  ❌ {feed_info['name']} error: {e}")

    print(f"\n📊 Total articles fetched: {len(all_articles)}")
    return all_articles

# ============================================================
# STEP 2: Gemini se Best Topics Choose karwao
# ============================================================
def choose_topics(articles, count=3):
    print(f"\n🤖 Gemini se top {count} topics choose karwa raha hoon...")

    articles_text = "\n".join([
        f"{i+1}. [{a['source']}] {a['title']}\n   Summary: {a['summary'][:200]}"
        for i, a in enumerate(articles[:30])
    ])

    prompt = f"""You are an AI news editor for AITechNews.co.in, an Indian tech news website.

Here are today's latest AI and tech news headlines:

{articles_text}

Select the TOP {count} most interesting and impactful stories for Indian tech audience.
Focus on: AI breakthroughs, new AI tools/products, tech industry news, India-relevant tech news.

Respond ONLY with a valid JSON array (no markdown, no extra text):
[
  {{
    "index": <original number from list>,
    "title": "<article title>",
    "reason": "<why this is important for Indian audience in 1 line>",
    "hindi_angle": "<unique Hindi/Indian angle for this story>"
  }}
]"""

    try:
        response = call_gemini(prompt, max_tokens=1000)
        # JSON parse karo
        clean = re.sub(r'```json|```', '', response).strip()
        topics = json.loads(clean)
        print(f"  ✅ {len(topics)} topics selected!")
        return topics
    except Exception as e:
        print(f"  ❌ Topic selection error: {e}")
        # Fallback: pehle {count} articles use karo
        return [{"index": i+1, "title": articles[i]["title"], "reason": "Top news", "hindi_angle": "Tech update"} for i in range(min(count, len(articles)))]

# ============================================================
# STEP 3: Gemini se Full Article Likhwao
# ============================================================
def write_article(topic, article_data):
    print(f"\n✍️  Article likh raha hoon: {topic['title'][:60]}...")

    prompt = f"""You are a professional tech journalist for AITechNews.co.in, an Indian AI news website.

Write a comprehensive, engaging news article in Hinglish (mix of Hindi and English) about:

Topic: {topic['title']}
Indian Angle: {topic.get('hindi_angle', 'Technology impact on India')}
Source Summary: {article_data.get('summary', '')}
Original Source: {article_data.get('source', 'Tech News')}

Article Requirements:
- Title: Catchy Hinglish title (under 70 chars)
- Length: 400-600 words
- Language: Hinglish (Hindi script + English tech terms)
- Structure: Introduction → Main Story → Indian Impact → Expert Opinion (imagined) → Conclusion
- Include: What happened, Why it matters, How it affects Indian users/businesses
- Tone: Informative but conversational, like talking to a tech-savvy friend
- SEO: Include relevant keywords naturally

Respond ONLY with valid JSON (no markdown):
{{
  "title": "Article title here",
  "slug": "url-friendly-slug-here",
  "excerpt": "2-3 line summary in Hinglish for preview",
  "content": "Full article content here with proper paragraphs. Use \\n\\n for paragraph breaks.",
  "tags": ["tag1", "tag2", "tag3", "tag4"],
  "category": "AI/Machine Learning/Tech News/Startups",
  "readTime": "3 min read",
  "language": "hinglish"
}}"""

    try:
        response = call_gemini(prompt, max_tokens=2000)
        clean = re.sub(r'```json|```', '', response).strip()
        article = json.loads(clean)
        print(f"  ✅ Article ready: {article.get('title', 'Unknown')[:50]}")
        return article
    except Exception as e:
        print(f"  ❌ Article writing error: {e}")
        return None

# ============================================================
# Gemini API Call
# ============================================================
def call_gemini(prompt, max_tokens=1000):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable set nahi hai!")

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
        }
    }

    response = requests.post(
        f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"Gemini API error {response.status_code}: {response.text[:200]}")

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

# ============================================================
# STEP 4: Articles Save karo
# ============================================================
def save_article(article, source_info):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = article.get("slug", "article").replace(" ", "-").lower()
    slug = re.sub(r'[^a-z0-9-]', '', slug)
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
# MAIN — Sab kuch chalao
# ============================================================
def main():
    print("=" * 60)
    print("🚀 AITechNews AI Agent — Gemini Edition")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print("=" * 60)

    # Step 1: News fetch karo
    all_news = fetch_news()
    if not all_news:
        print("❌ Koi news nahi mili! Exiting.")
        return

    # Step 2: Best topics choose karo
    selected_topics = choose_topics(all_news, count=ARTICLES_TO_WRITE)

    # Step 3 & 4: Articles likho aur save karo
    print(f"\n📝 {len(selected_topics)} articles likhna shuru...")
    written = []

    for i, topic in enumerate(selected_topics):
        idx = topic.get("index", i+1) - 1
        source_article = all_news[min(idx, len(all_news)-1)]

        article = write_article(topic, source_article)
        if article:
            filename = save_article(article, source_article)
            written.append(filename)
            time.sleep(2)  # Rate limiting ke liye

    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Done! {len(written)} articles successfully likhe gaye:")
    for f in written:
        print(f"   📄 {f}")
    print("=" * 60)
    print("🌐 Vercel deploy hoga automatically via GitHub Actions!")

if __name__ == "__main__":
    main()
