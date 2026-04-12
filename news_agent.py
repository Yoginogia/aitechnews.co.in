"""
AITechNews - Agentic AI Article Writer
Roz subah latest tech/AI news dhundh ke Hindi+English article likhta hai
aur GitHub pe push karta hai jisse Vercel auto-deploy karta hai.
"""

import os
import json
import re
import time
import datetime
import feedparser
import anthropic
import requests
from pathlib import Path


# ===== CONFIG =====
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
ARTICLES_DIR   = Path("articles")        # JSON articles yahan save honge
MAX_ARTICLES   = 3                       # Roz kitne articles likhne hain
IST_OFFSET     = 5.5                     # India Standard Time offset

# ===== NEWS SOURCES (Free RSS Feeds) =====
RSS_FEEDS = [
    # AI News
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/",  "category": "AI Tools"},
    {"url": "https://feeds.feedburner.com/venturebeat/SZYF",                  "category": "AI Tools"},
    {"url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml","category": "AI Tools"},
    # Gadgets / Phones
    {"url": "https://feeds.feedburner.com/ndtvgadgets",                        "category": "Gadgets"},
    {"url": "https://www.91mobiles.com/hub/feed/",                             "category": "Gadgets"},
    {"url": "https://www.gsmarena.com/rss-news-reviews.php3",                  "category": "Gadgets"},
    # India Tech
    {"url": "https://techpp.com/feed/",                                        "category": "Software Updates"},
    {"url": "https://www.gadgets360.com/rss/news",                             "category": "Gadgets"},
    # Crypto
    {"url": "https://cointelegraph.com/rss",                                   "category": "Crypto"},
]

# ===== CATEGORIES =====
CATEGORY_SLUGS = {
    "AI Tools":          "ai-tools",
    "Gadgets":           "gadgets",
    "Software Updates":  "software-updates",
    "Crypto":            "crypto",
    "Best Phones":       "best-phones",
}


def get_ist_now():
    """Current IST datetime"""
    utc = datetime.datetime.utcnow()
    ist = utc + datetime.timedelta(hours=IST_OFFSET)
    return ist


def fetch_latest_news(max_per_feed=5):
    """Saare RSS feeds se latest news fetch karo"""
    print("📡 RSS feeds se news fetch kar raha hoon...")
    all_news = []
    today = get_ist_now().date()

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:max_per_feed]:
                # Title aur summary extract karo
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")
                # Strip HTML tags from summary
                summary = re.sub(r"<[^>]+>", "", summary)[:800]

                if not title or len(title) < 10:
                    continue

                # Date check - sirf aaj ya kal ki news
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_date = datetime.date(*published[:3])
                    days_old = (today - pub_date).days
                    if days_old > 2:
                        continue

                all_news.append({
                    "title":    title,
                    "summary":  summary,
                    "link":     link,
                    "category": feed_info["category"],
                    "source":   feed.feed.get("title", "Unknown"),
                })
        except Exception as e:
            print(f"  ⚠️  Feed error ({feed_info['url'][:40]}): {e}")

    print(f"  ✅ {len(all_news)} news items mili")
    return all_news


def select_best_topics(news_list, count=MAX_ARTICLES):
    """AI se best topics select karao"""
    if not news_list:
        return []

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    news_text = "\n".join([
        f"{i+1}. [{item['category']}] {item['title']} — {item['summary'][:200]}"
        for i, item in enumerate(news_list[:40])
    ])

    prompt = f"""You are an editor for AITechNews, an Indian tech news website in Hindi+English.

From this list of latest tech news, select the TOP {count} most interesting stories for Indian readers.
Prefer: AI tools news, Indian phone launches, price changes, 5G news, app updates.
Avoid: US politics, sports, non-tech news.

NEWS LIST:
{news_text}

Return ONLY a JSON array with the selected item numbers (1-indexed), like: [3, 7, 12]
Return ONLY valid JSON, nothing else."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        indices = json.loads(response.content[0].text.strip())
        selected = [news_list[i-1] for i in indices if 0 < i <= len(news_list)]
        print(f"  🎯 {len(selected)} topics select kiye")
        return selected[:count]
    except Exception as e:
        print(f"  ⚠️ Topic selection error: {e} — first {count} le raha hoon")
        return news_list[:count]


def generate_article(topic, existing_slugs):
    """Claude se full Hindi+English article generate karo"""
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    ist_now  = get_ist_now()
    date_str = ist_now.strftime("%Y-%m-%d")
    time_str = ist_now.strftime("%H:%M")

    prompt = f"""You are a senior tech journalist for AITechNews.co.in — India's leading Hindi+English tech news website.

Write a COMPLETE, detailed news article about this topic:

TOPIC: {topic['title']}
CATEGORY: {topic['category']}
BACKGROUND: {topic['summary']}
SOURCE: {topic['source']}

ARTICLE REQUIREMENTS:
- Language: Hinglish (Hindi + English mix) — jaise Indian tech channels likhte hain
- Length: 600-800 words (comprehensive, not just summary)
- Structure: Intro → Details → India Impact → Expert Take → Conclusion
- Include: Practical tips for Indian users, pricing in INR where relevant
- Tone: Friendly, conversational, like talking to a friend
- SEO: Include relevant keywords naturally

OUTPUT FORMAT — Return ONLY this exact JSON (no markdown, no backticks):
{{
  "title": "Catchy Hindi+English title (max 70 chars)",
  "slug": "url-friendly-slug-no-hindi-chars",
  "category": "{topic['category']}",
  "date": "{date_str}",
  "readTime": "4 min read",
  "excerpt": "2-3 line summary in Hinglish (max 160 chars for SEO)",
  "content": "Full article HTML content with <h2>, <p>, <ul>, <strong> tags",
  "tags": ["tag1", "tag2", "tag3", "tag4"],
  "metaTitle": "SEO title (max 60 chars)",
  "metaDescription": "SEO description (max 155 chars)",
  "image": "/images/blog/auto-generated-placeholder.jpg",
  "source": "{topic['source']}",
  "sourceUrl": "{topic['link']}"
}}"""

    print(f"  ✍️  Article likh raha hoon: {topic['title'][:50]}...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # Clean JSON if wrapped in markdown
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    article = json.loads(raw)

    # Slug uniqueness ensure karo
    base_slug = article["slug"]
    slug      = base_slug
    counter   = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1
    article["slug"] = slug

    return article


def save_article(article):
    """Article ko JSON file mein save karo"""
    ARTICLES_DIR.mkdir(exist_ok=True)
    filepath = ARTICLES_DIR / f"{article['slug']}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(article, f, ensure_ascii=False, indent=2)
    print(f"  💾 Saved: {filepath}")
    return filepath


def update_index(new_articles):
    """articles/index.json update karo — website yahi read karti hai"""
    index_path = ARTICLES_DIR / "index.json"

    # Existing index load karo
    if index_path.exists():
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = []

    # Naye articles prepend karo
    for article in reversed(new_articles):
        entry = {
            "slug":      article["slug"],
            "title":     article["title"],
            "category":  article["category"],
            "date":      article["date"],
            "excerpt":   article["excerpt"],
            "readTime":  article["readTime"],
            "image":     article.get("image", "/images/blog/default.jpg"),
            "tags":      article.get("tags", []),
        }
        # Duplicate check
        existing_slugs = [e["slug"] for e in index]
        if entry["slug"] not in existing_slugs:
            index.insert(0, entry)

    # Latest 500 articles rakhna — baaki archive karo
    index = index[:500]

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"  📋 Index updated — total {len(index)} articles")


def run_agent():
    """Main agent — yeh GitHub Actions roz subah call karta hai"""
    ist = get_ist_now()
    print(f"\n🤖 AITechNews AI Agent starting — {ist.strftime('%d %b %Y, %I:%M %p')} IST")
    print("=" * 60)

    if not CLAUDE_API_KEY:
        raise ValueError("❌ CLAUDE_API_KEY environment variable set nahi hai!")

    # Step 1: News fetch karo
    news = fetch_latest_news(max_per_feed=6)
    if not news:
        print("⚠️ Koi news nahi mili — exit kar raha hoon")
        return

    # Step 2: Best topics select karo
    print("\n🧠 Best topics select kar raha hoon...")
    topics = select_best_topics(news, count=MAX_ARTICLES)

    # Step 3: Existing slugs load karo (duplicates avoid karne ke liye)
    index_path = ARTICLES_DIR / "index.json"
    existing_slugs = set()
    if index_path.exists():
        with open(index_path, encoding="utf-8") as f:
            existing_slugs = {a["slug"] for a in json.load(f)}

    # Step 4: Har topic ke liye article likho
    print(f"\n✍️  {len(topics)} articles likh raha hoon...")
    written = []
    for i, topic in enumerate(topics, 1):
        print(f"\n  [{i}/{len(topics)}]")
        try:
            article = generate_article(topic, existing_slugs)
            existing_slugs.add(article["slug"])
            filepath = save_article(article)
            written.append(article)
            print(f"  ✅ Done: {article['title'][:50]}")
            time.sleep(2)  # Rate limiting
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    # Step 5: Index update karo
    if written:
        print(f"\n📋 Index update kar raha hoon...")
        update_index(written)

    # Step 6: Summary
    print("\n" + "=" * 60)
    print(f"✅ COMPLETE! {len(written)}/{len(topics)} articles likhe")
    for a in written:
        print(f"   📄 [{a['category']}] {a['title'][:55]}")
    print(f"\n🌐 Vercel deploy automatically trigger hoga GitHub push pe")
    print("=" * 60)


if __name__ == "__main__":
    run_agent()
