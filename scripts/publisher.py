#!/usr/bin/env python3
"""
AITechNews Publisher v3.0 - MEGA UPDATE
- 10 Articles Daily (AI x5, Deals x2, Software x1, Crypto x2)
- Strict Devanagari + English Hinglish (matches existing site style)
- Auto-post to Telegram + Twitter (with category-specific hashtags)
- Hyper-realistic HuggingFace images
- Runs at 00:00 UTC (5:30 AM IST)
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

# Facebook
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "61574185597579")

GITHUB_REPO = "Yoginogia/aitechindia"
CONTENT_PATH = "src/content/blog"
IMAGE_PATH = "public/images/blog"

if GEMINI_API_KEY and HAS_GEMINI:
    genai.configure(api_key=GEMINI_API_KEY)

# =============================================================================
# CATEGORY CONFIGURATION - Multi-Category News Engine
# =============================================================================
CATEGORY_CONFIG = {
    "AI": {
        "count": 5,
        "feeds": [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://venturebeat.com/ai/feed/",
            "https://blog.google/technology/ai/rss/",
            "https://openai.com/blog/rss.xml",
            "https://analyticsindiamag.com/feed/",
            "https://www.91mobiles.com/hub/feed/",
            "https://gadgets.ndtv.com/rss/feeds",
        ],
        "hashtags": "#AINews #TechIndia #ArtificialIntelligence",
        "image_style": "futuristic AI neural network, glowing circuits, holographic display, dark background",
    },
    "Deals": {
        "count": 2,
        "feeds": [
            "https://feeds.feedburner.com/Techcrunch",
            "https://www.techradar.com/rss",
            "https://www.91mobiles.com/hub/feed/",
            "https://www.gsmarena.com/rss-news-reviews.php3",
        ],
        "hashtags": "#TopDeals #AmazonIndia #TechDeals #BuyNow",
        "image_style": "shopping sale discount, product showcase, vibrant red sale banner, tech gadgets",
    },
    "Software": {
        "count": 1,
        "feeds": [
            "https://www.bleepingcomputer.com/feed/",
            "https://betanews.com/feed/",
            "https://www.ghacks.net/feed/",
            "https://techcrunch.com/software/feed/",
        ],
        "hashtags": "#SoftwareUpdate #TechNews #Apps #Windows",
        "image_style": "software update screen, code on monitor, download progress bar, dark blue tech background",
    },
    "Crypto": {
        "count": 2,
        "feeds": [
            "https://cointelegraph.com/rss",
            "https://coindesk.com/arc/outboundfeeds/rss/",
            "https://cryptonews.com/news/feed/",
            "https://decrypt.co/feed",
        ],
        "hashtags": "#Crypto #Bitcoin #Blockchain #CryptoIndia",
        "image_style": "bitcoin cryptocurrency golden coins, blockchain visualization, financial charts, dark premium background",
    },
}

# =============================================================================
# Exact writing style prompt based on EXISTING site articles
# =============================================================================
HINGLISH_STYLE_EXAMPLE = """
Economic Times की रिपोर्ट के अनुसार, भारत में AI और Cloud Computing की वजह से Data Centers की Demand तेज़ी से Double हो रही है।
Google, Microsoft और Amazon भारत में Billions Invest कर रहे हैं।
आप जब ChatGPT से सवाल पूछते हैं, YouTube पर Video देखते हैं, या WhatsApp पर Message भेजते हैं — यह सब हज़ारों Computers से मिलकर बने विशाल "Data Centers" में Process होता है।
AI का इस्तेमाल जितना बढ़ रहा है, उतना ही ज़्यादा Computing Power की ज़रूरत बढ़ रही है।
"""

def fetch_news_for_category(category: str) -> list[dict]:
    """Fetch news from category-specific RSS feeds."""
    news = []
    feeds = CATEGORY_CONFIG[category]["feeds"]
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                title = entry.get("title", "").strip()
                summary_raw = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r'<[^>]+>', '', summary_raw).strip()[:500]
                if title and len(title) > 20:
                    news.append({
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", ""),
                        "category": category
                    })
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
    return news

def parse_json_response(response_text: str) -> Optional[dict]:
    try:
        clean = re.sub(r'```json|```', '', response_text).strip()
        start_idx = clean.find('{')
        end_idx = clean.rfind('}') + 1
        if start_idx >= 0 and end_idx > start_idx:
            return json.loads(clean[start_idx:end_idx])
    except Exception as e:
        print(f"  JSON parse error: {e}")
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
            "max_tokens": 2500,
            "temperature": 0.7
        },
        timeout=90
    )
    return response.json()["choices"][0]["message"]["content"]

def generate_and_upload_hf_image(title: str, slug: str, category: str) -> str:
    image_style = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["AI"])["image_style"]
    
    if not HF_TOKEN:
        print("  HF_TOKEN missing! Falling back to Pollinations.")
        encoded = title.replace(" ", "%20")[:100]
        return f"https://image.pollinations.ai/prompt/{encoded}%20{image_style.replace(' ', '%20')}?width=1200&height=630&nologo=true"
    
    print("  Generating HF image via SDXL...")
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    prompt = f"hyperrealistic, extremely detailed, cinematic lighting, 8k resolution, masterpiece, {image_style}, photorealistic, professional photography"
    
    for attempt in range(2):
        try:
            response = requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=120)
            if response.status_code == 200 and len(response.content) > 5000:
                image_filename = f"{slug}.jpg"
                if push_file_to_github(f"{IMAGE_PATH}/{image_filename}", response.content, is_binary=True):
                    print(f"  Image uploaded: {image_filename}")
                    return f"/images/blog/{image_filename}"
        except Exception as e:
            print(f"  HF attempt {attempt+1} failed: {e}")
        time.sleep(10)
    
    print("  Falling back to Pollinations.")
    encoded = title.replace(" ", "%20")[:100]
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true"

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
        "message": f"Auto: {filepath.split('/')[-1]}",
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(url, headers=headers, json=payload)
    success = put_response.status_code in [200, 201]
    if not success:
        print(f"  GitHub push failed: {put_response.status_code} - {put_response.text[:200]}")
    return success

def post_to_telegram(title: str, slug: str, image_url: str, category: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [Telegram] Skipping: Credentials not set.")
        return
    
    article_url = f"https://aitechnews.co.in/blog/{slug}"
    chat_id = TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID.startswith('@') or TELEGRAM_CHAT_ID.startswith('-') else f"@{TELEGRAM_CHAT_ID}"
    hashtags = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["AI"])["hashtags"]
    
    category_emoji = {"AI": "🤖", "Deals": "🛍️", "Software": "💻", "Crypto": "₿"}.get(category, "📰")
    caption = f"{category_emoji} *{title}*\n\n👉 [Full Article]({article_url})\n\n{hashtags}"
    
    photo_url = f"https://aitechnews.co.in{image_url}" if image_url.startswith("/") else image_url
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    try:
        res = requests.post(url, json={
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "Markdown"
        }, timeout=30)
        if res.status_code == 200:
            print("  Telegram: SUCCESS")
        else:
            # Retry without photo
            url2 = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url2, json={
                "chat_id": chat_id,
                "text": caption + f"\n\n{article_url}",
                "parse_mode": "Markdown"
            }, timeout=30)
            print(f"  Telegram: Sent as text (photo failed: {res.status_code})")
    except Exception as e:
        print(f"  Telegram Error: {e}")

def post_to_twitter(title: str, slug: str, category: str):
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
        hashtags = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["AI"])["hashtags"]
        
        # Keep tweet under 270 chars
        max_title_len = 200 - len(article_url) - len(hashtags)
        short_title = title[:max_title_len] if len(title) > max_title_len else title
        tweet_text = f"{short_title}\n\n{article_url}\n\n{hashtags}"
        
        client.create_tweet(text=tweet_text)
        print("  Twitter: SUCCESS")
    except Exception as e:
        print(f"  Twitter Error: {e}")

def post_to_facebook(title: str, slug: str, image_url: str, category: str):
    if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
        print("  [Facebook] Skipping: Credentials not set.")
        return
    try:
        article_url = f"https://aitechnews.co.in/blog/{slug}"
        hashtags = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["AI"])["hashtags"]
        message = f"{title}\n\n{article_url}\n\n{hashtags}"
        
        photo_url = f"https://aitechnews.co.in{image_url}" if image_url.startswith("/") else image_url
        
        # Try photo post first
        api_url = f"https://graph.facebook.com/v22.0/{FB_PAGE_ID}/photos"
        res = requests.post(api_url, data={
            "url": photo_url,
            "caption": message,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }, timeout=30)
        
        if res.status_code == 200:
            print("  Facebook: SUCCESS")
        else:
            # Fallback: text post with link
            feed_url = f"https://graph.facebook.com/v22.0/{FB_PAGE_ID}/feed"
            requests.post(feed_url, data={
                "message": message,
                "link": article_url,
                "access_token": FB_PAGE_ACCESS_TOKEN
            }, timeout=30)
            print(f"  Facebook: Sent as link post")
    except Exception as e:
        print(f"  Facebook Error: {e}")

def generate_article(item: dict, category: str) -> Optional[dict]:
    """Generate article matching EXACT style of existing aitechnews.co.in articles."""
    
    category_instructions = {
        "AI": "AI aur Technology news ke baare mein likhein.",
        "Deals": "Amazon/Flipkart par milne wale best tech deals aur discounts ke baare mein likhein. Price, original MRP, discount percentage zaroor mention karein.",  
        "Software": "Software update, naye features ya security patch ke baare mein likhein. Versions aur changes clearly batayein.",
        "Crypto": "Cryptocurrency market news ke baare mein likhein. Bitcoin, Ethereum ya altcoin prices aur trends mention karein.",
    }

    prompt = f"""You are the expert writer for AITechNews.co.in — India's top Hinglish tech news website.

News Topic: "{item['title']}"
Context: {item['summary'][:400]}
Category: {category}
Task: {category_instructions.get(category, "")}

WRITING STYLE — Follow this EXACT style (from our existing published articles):
---
"Economic Times की रिपोर्ट के अनुसार, भारत में AI और Cloud Computing की वजह से Data Centers की Demand तेज़ी से Double हो रही है।"
"आप जब ChatGPT से सवाल पूछते हैं, YouTube पर Video देखते हैं — यह सब हज़ारों Computers से मिलकर बने विशाल Data Centers में Process होता है।"
"AI का इस्तेमाल जितना बढ़ रहा है, उतना ही ज़्यादा Computing Power की ज़रूरत बढ़ रही है।"
---

STRICT LANGUAGE RULES (These CANNOT be violated):
1. Sentence structure aur narrative MUST be in Devanagari Hindi script (हिंदी).
   WRONG: "Is article mein hum baat karenge..." 
   RIGHT: "इस article में हम बात करेंगे..."
2. ALL technical terms (AI, CPU, Bitcoin, App, Download, Update, Deal, Price, etc.) stay in English script.
3. Headings: Mix of Devanagari + English, each heading MUST end with an emoji.
   Example: "भारत में AI का 'Gold Rush' शुरू! Data Centers की Demand Double 📈"
4. Use **bold** for all English technical terms and important numbers.
5. Write 500+ words. Use \\n\\n between paragraphs.

Respond ONLY with raw JSON (NO markdown, NO backticks):
{{"title":"Catchy Hinglish title with emoji under 90 chars (हिंदी + English mix)","slug":"url-slug-english-only-no-special-chars","excerpt":"2-3 line Hinglish preview for SEO (हिंदी + English mix)","content":"Full article in exact Hinglish style described above using \\n\\n between paragraphs","category":"{category}","readingTime":"5 min read"}}"""
    
    try:
        response = call_ai(prompt)
        return parse_json_response(response)
    except Exception as e:
        print(f"  Text Generation error: {e}")
        return None

def create_markdown(article: dict, today_formatted: str, image_url: str) -> str:
    title = article['title'].replace('"', "'").replace('\n', ' ')
    excerpt = article['excerpt'].replace('"', "'").replace('\n', ' ')
    category = article.get('category', 'AI')
    reading_time = article.get('readingTime', '5 min read')

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

def publish_category(category: str, today_formatted: str, today_slug: str) -> int:
    """Fetch, generate, and publish articles for a given category."""
    config = CATEGORY_CONFIG[category]
    count = config["count"]
    
    print(f"\n{'='*60}")
    print(f"  CATEGORY: {category} ({count} articles)")
    print(f"{'='*60}")
    
    news = fetch_news_for_category(category)
    if not news:
        print(f"  No news found for {category}. Skipping.")
        return 0
    
    # Pick evenly spaced items
    selected = news[::max(1, len(news) // count)][:count]
    published = 0
    
    for i, item in enumerate(selected):
        print(f"\n  Article {i+1}/{count}: {item['title'][:60]}...")
        try:
            article = generate_article(item, category)
            if not article:
                print("  Skipping - generation failed")
                continue

            slug = re.sub(r'[^a-z0-9-]', '', article.get("slug", "tech-news").lower().replace(' ', '-'))[:50]
            slug = slug.strip('-')
            filename = f"{category.lower()}-{slug}-{today_slug}.md"
            
            image_url = generate_and_upload_hf_image(item['title'][:80], slug, category)
            md_content = create_markdown(article, today_formatted, image_url)
            
            if push_file_to_github(f"{CONTENT_PATH}/{filename}", md_content, is_binary=False):
                published += 1
                print(f"  Published: {filename}")
                
                clean_slug = filename.replace('.md', '')
                post_to_telegram(article['title'], clean_slug, image_url, category)
                post_to_twitter(article['title'], clean_slug, category)
                post_to_facebook(article['title'], clean_slug, image_url, category)
            
            time.sleep(8)  # Rate limiting buffer

        except Exception as e:
            print(f"  Error: {e}")
    
    return published

def main():
    print("=" * 60)
    print("=== AITechNews Publisher v3.0 - MEGA UPDATE ===")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
    print("Categories: AI(5) + Deals(2) + Software(1) + Crypto(2) = 10 articles")
    print("=" * 60)

    today_formatted = datetime.now(timezone.utc).strftime("%d %B %Y")
    today_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    total_published = 0
    for category in CATEGORY_CONFIG.keys():
        published = publish_category(category, today_formatted, today_slug)
        total_published += published
        time.sleep(5)

    print(f"\n{'='*60}")
    print(f"DONE! Total: {total_published}/10 articles published today!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
