#!/usr/bin/env python3
"""
AITechNews Publisher v4.0 - ULTRA UPDATE
- FIX 1: Article Deduplication (30-day history, no repeats)
- FIX 2: Casual Hinglish (natural mix, NOT shuddh Hindi)
- NEW: Web Stories auto-generation (AMP format for Google Discover)
- NEW: Amazon India real deals RSS feeds
- 12 Articles Daily: AI(5) + Gadgets(2) + Deals(2) + Software(1) + Crypto(2)
"""

import os
import json
import feedparser
import requests
import re
import time
import base64
from datetime import datetime, timezone, timedelta
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

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "61574185597579")

GITHUB_REPO = "Yoginogia/aitechindia"
CONTENT_PATH = "src/content/blog"
IMAGE_PATH = "public/images/blog"
STORIES_DATA_PATH = "src/data/stories.ts"
HISTORY_PATH = "scripts/published_history.json"

if GEMINI_API_KEY and HAS_GEMINI:
    genai.configure(api_key=GEMINI_API_KEY)

# =============================================================================
# CATEGORY CONFIGURATION - v4.0 with Amazon India Deals feeds
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
        "emoji": "🤖",
        "color": "#8b5cf6",
    },
    "Deals": {
        "count": 2,
        "feeds": [
            # Amazon India affiliate & deal RSS feeds
            "https://www.91mobiles.com/hub/category/deals/feed/",
            "https://www.smartprix.com/bytes/feed/?cat=deals",
            "https://www.reootz.com/deals/feed/",
            "https://www.dealnloot.com/feed/",
            "https://www.desidime.com/deals.rss",
            "https://gizmochina.com/feed/",
            "https://www.digit.in/rss/deals-offers.xml",
        ],
        "hashtags": "#TopDeals #AmazonIndia #TechDeals #BuyNow",
        "image_style": "amazon india sale, tech gadget discount, red sale tag, smartphone laptop deal, vibrant shopping banner",
        "emoji": "🛍️",
        "color": "#ef4444",
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
        "emoji": "💻",
        "color": "#3b82f6",
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
        "emoji": "₿",
        "color": "#f59e0b",
    },
    "Gadgets": {
        "count": 2,
        "feeds": [
            "https://www.91mobiles.com/hub/category/news/feed/",
            "https://www.autocarindia.com/rss/news",
            "https://electrek.co/feed/",
            "https://gadgets360.com/rss/news",
            "https://www.techradar.com/rss",
        ],
        "hashtags": "#Gadgets #EVIndia #Smartphones #TechNews",
        "image_style": "futuristic smartphone, electric vehicle car, sleek modern tech, studio lighting, hyperrealistic glowing reflections",
        "emoji": "📱",
        "color": "#ec4899",
    },
}

# =============================================================================
# FIX 2: CASUAL HINGLISH STYLE (Not Shuddh Hindi!)
# Writing style that matches ACTUAL existing articles on the site
# =============================================================================
HANGING_STYLE_EXAMPLE = """
GOOD (Devanagari Hindi + English Tech Terms - matches our site):
- "यार, अब imagine करो — ChatGPT से सवाल पूछो, YouTube पर video देखो — ये सब 'Data Centers' में process होता है!"
- "Google, Microsoft और Amazon सब अपना पैसा India में लगा रहे हैं — और क्यों ना लगाएं? Market जो है!"
- "तो अगर आप सोच रहे हो कि ये news सिर्फ बड़े लोगों के लिए है — बिल्कुल गलत!"
- "सीधी बात करते हैं — **Bitcoin** अभी ₹58 लाख के पास है, और experts बोल रहे हैं..."

BAD (Roman Hindi / Pure English - DO NOT write like this):
- "Yaar, ye bahut badi khabar hai." ❌ (Must use Devanagari: यार, ये बहुत बड़ी खबर है।)
- "Aaj hum tech ke baare mein baat karenge." ❌
- "यह एक महत्वपूर्ण समाचार है।" ❌ (Too formal/shuddh)
"""

# =============================================================================
# FIX 1: DEDUPLICATION SYSTEM - 30-day article history
# =============================================================================
def load_published_history() -> dict:
    """Load published article history from GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            content = base64.b64decode(response.json()["content"]).decode("utf-8")
            return json.loads(content)
    except Exception as e:
        print(f"  History load error (first run?): {e}")
    return {"published": []}

def save_published_history(history: dict, new_titles: list):
    """Save updated published history to GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    sha = None
    check = requests.get(url, headers=headers, timeout=15)
    if check.status_code == 200:
        sha = check.json().get("sha")

    # Keep only last 30 days of entries
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    existing = [
        e for e in history.get("published", [])
        if e.get("date", "") > thirty_days_ago
    ]
    today = datetime.now().isoformat()
    for title in new_titles:
        existing.append({"title": title.lower(), "date": today})

    new_history = {"published": existing}
    content_str = json.dumps(new_history, ensure_ascii=False, indent=2)
    encoded = base64.b64encode(content_str.encode("utf-8")).decode("ascii")

    payload = {
        "message": "Auto: Update published history (deduplication)",
        "content": encoded,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    try:
        res = requests.put(url, headers=headers, json=payload, timeout=15)
        if res.status_code in [200, 201]:
            print(f"  ✓ History saved ({len(existing)} entries total)")
        else:
            print(f"  ✗ History save failed: {res.status_code}")
    except Exception as e:
        print(f"  History save error: {e}")

def is_duplicate(title: str, history: dict) -> bool:
    """Check if article title overlaps >50% with recently published articles."""
    title_words = set(re.sub(r'[^\w\s]', '', title.lower()).split())
    # Remove very common words from comparison
    stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'is', 'are', 'was', 'of', 'to', 'for', 'and', 'or', '2026', 'india', 'new', 'how'}
    title_words -= stop_words

    if len(title_words) < 3:
        return False

    for entry in history.get("published", []):
        existing_words = set(re.sub(r'[^\w\s]', '', entry.get("title", "")).split()) - stop_words
        if not existing_words:
            continue
        overlap = len(title_words & existing_words) / max(len(title_words), 1)
        if overlap > 0.5:
            print(f"  ⏭ Duplicate ({overlap:.0%} overlap) with: {entry['title'][:50]}")
            return True
    return False

# =============================================================================
# WEB STORIES AUTO-GENERATION
# =============================================================================
def generate_story_slides(title: str, excerpt: str, category: str) -> list:
    """Generate 4 concise slides for web story."""
    prompt = f"""Create a Google Web Story in exactly 4 short slides.
Article: {title}
Summary: {excerpt}

Rules:
- Each slide: 1 heading (max 8 words) + 1-2 lines of body text (max 20 words)
- Language: Casual Hinglish (Hindi words in Devanagari + English tech terms)
- Slide 1: 🔥 Breaking hook
- Slide 2: Key fact / What happened
- Slide 3: India ke liye kya matlab
- Slide 4: "Poori Khabar Padhein →" CTA

Return ONLY a raw JSON array, no markdown, no backticks:
[
  {{"heading": "heading with emoji", "text": "1-2 line body"}},
  {{"heading": "heading", "text": "1-2 line body"}},
  {{"heading": "heading", "text": "1-2 line body"}},
  {{"heading": "Poori Khabar Padhein →", "text": "AITechNews.co.in par abhi padhein!"}}
]"""
    try:
        response = call_ai(prompt)
        clean = re.sub(r'```json|```', '', response).strip()
        start, end = clean.find('['), clean.rfind(']') + 1
        if start >= 0 and end > start:
            return json.loads(clean[start:end])
    except Exception as e:
        print(f"  Slide gen error: {e}")

    # Fallback slides
    return [
        {"heading": f"🔥 {title[:55]}", "text": excerpt[:100]},
        {"heading": "Kya Hua? 📰", "text": "Aaj ki sabse badi tech khabar!"},
        {"heading": "India ke Liye Khaas! 🇮🇳", "text": "Ye news aapki life par seedha asar daal sakti hai!"},
        {"heading": "Poori Khabar Padhein →", "text": "AITechNews.co.in par abhi padhein!"}
    ]

def build_amp_html(story_slug: str, title: str, subtitle: str, category: str, image_url: str, slides: list, article_url: str) -> str:
    """Build AMP Web Story HTML file."""
    cat_color = CATEGORY_CONFIG.get(category, {}).get("color", "#8b5cf6")
    cat_emoji = CATEGORY_CONFIG.get(category, {}).get("emoji", "📰")
    full_image = f"https://aitechnews.co.in{image_url}" if image_url.startswith("/") else image_url

    pages_html = ""
    for i, slide in enumerate(slides):
        is_last = (i == len(slides) - 1)
        cta = f'<a class="cta-btn" href="{article_url}">Poori Khabar Padhein →</a>' if is_last else ""
        pages_html += f"""
  <amp-story-page id="slide{i+1}">
    <amp-story-grid-layer template="fill">
      <amp-img src="{full_image}" width="720" height="1280" layout="fill" object-fit="cover"></amp-img>
    </amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="overlay">
      <div class="slide-content">
        <div class="badge" style="background:{cat_color}">{cat_emoji} {category}</div>
        <h1 class="heading">{slide['heading']}</h1>
        <p class="body-text">{slide['text']}</p>
        {cta}
      </div>
    </amp-story-grid-layer>
  </amp-story-page>"""

    return f"""<!doctype html>
<html amp lang="hi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
  <title>{title}</title>
  <meta name="description" content="{subtitle}">
  <link rel="canonical" href="{article_url}">
  <script async src="https://cdn.ampproject.org/v0.js"></script>
  <script async custom-element="amp-story" src="https://cdn.ampproject.org/v0/amp-story-1.0.js"></script>
  <style amp-boilerplate>body{{-webkit-animation:-amp-start 8s steps(1,end) 0s 1 normal both;-moz-animation:-amp-start 8s steps(1,end) 0s 1 normal both;-ms-animation:-amp-start 8s steps(1,end) 0s 1 normal both;animation:-amp-start 8s steps(1,end) 0s 1 normal both}}@-webkit-keyframes -amp-start{{from{{visibility:hidden}}to{{visibility:visible}}}}@-moz-keyframes -amp-start{{from{{visibility:hidden}}to{{visibility:visible}}}}@-ms-keyframes -amp-start{{from{{visibility:hidden}}to{{visibility:visible}}}}@keyframes -amp-start{{from{{visibility:hidden}}to{{visibility:visible}}}}</style><noscript><style amp-boilerplate>body{{-webkit-animation:none;-moz-animation:none;-ms-animation:none;animation:none}}</style></noscript>
  <style amp-custom>
    amp-story {{ font-family: 'Noto Sans', sans-serif; }}
    .overlay {{ background: linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.3) 60%, transparent 100%); width:100%; height:100%; position:absolute; bottom:0; }}
    .slide-content {{ position:absolute; bottom:0; left:0; right:0; padding:36px 28px; }}
    .badge {{ display:inline-block; color:#fff; font-size:11px; font-weight:800; padding:6px 14px; border-radius:20px; text-transform:uppercase; letter-spacing:1px; margin-bottom:14px; }}
    .heading {{ color:#fff; font-size:28px; font-weight:900; line-height:1.2; margin:0 0 12px; text-shadow:0 2px 8px rgba(0,0,0,0.6); }}
    .body-text {{ color:rgba(255,255,255,0.85); font-size:15px; line-height:1.6; margin:0 0 18px; }}
    .cta-btn {{ display:inline-block; background:{cat_color}; color:#fff; padding:13px 26px; border-radius:50px; font-size:14px; font-weight:800; text-decoration:none; }}
  </style>
</head>
<body>
  <amp-story standalone title="{title}" publisher="AITechNews India"
    publisher-logo-src="https://aitechnews.co.in/logo.png"
    poster-portrait-src="{full_image}">
    {pages_html}
  </amp-story>
</body>
</html>"""

def add_story_to_stories_ts(article: dict, story_slug: str, image_url: str, category: str, pages: int):
    """Prepend new story entry to src/data/stories.ts on GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{STORIES_DATA_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        print(f"  ✗ Could not fetch stories.ts: {resp.status_code}")
        return

    existing_content = base64.b64decode(resp.json()["content"]).decode("utf-8")
    sha = resp.json().get("sha")

    cat_color = CATEGORY_CONFIG.get(category, {}).get("color", "#8b5cf6")
    cat_emoji = CATEGORY_CONFIG.get(category, {}).get("emoji", "📰")
    title_safe = article["title"][:60].replace("'", "\\'").replace("\n", " ")
    subtitle_safe = article.get("excerpt", "")[:100].replace("'", "\\'").replace("\n", " ")
    img = f"/images/blog/{story_slug.replace('story-', '')}.jpg" if image_url.startswith("/") else image_url

    new_entry = f"""    {{
        slug: '{story_slug}',
        title: '{title_safe}',
        subtitle: '{subtitle_safe}',
        category: '{cat_emoji} {category}',
        categoryColor: '{cat_color}',
        image: '{img}',
        pages: {pages},
        isTrending: true,
    }},"""

    # Insert right after "export const STORIES: StoryItem[] = ["
    marker = "export const STORIES: StoryItem[] = ["
    if marker in existing_content:
        pos = existing_content.find(marker) + len(marker)
        updated = existing_content[:pos] + "\n" + new_entry + existing_content[pos:]

        encoded = base64.b64encode(updated.encode("utf-8")).decode("ascii")
        put_resp = requests.put(url, headers=headers, json={
            "message": f"Auto: Add web story — {article['title'][:40]}",
            "content": encoded,
            "sha": sha,
            "branch": "main"
        }, timeout=15)
        if put_resp.status_code in [200, 201]:
            print(f"  ✓ stories.ts updated")
        else:
            print(f"  ✗ stories.ts update failed: {put_resp.status_code}")

def publish_web_story(article: dict, slug: str, image_url: str, category: str, article_url: str):
    """Generate AMP story HTML and update stories.ts."""
    print(f"  Generating Web Story...")
    slides = generate_story_slides(article["title"], article.get("excerpt", ""), category)
    story_slug = f"{category.lower()}-story-{slug}"

    amp_html = build_amp_html(story_slug, article["title"], article.get("excerpt", ""),
                              category, image_url, slides, article_url)

    # Push AMP HTML file
    html_path = f"public/web-stories/{story_slug}.html"
    if push_file_to_github(html_path, amp_html):
        print(f"  ✓ Web Story: {story_slug}.html")

    # Update stories.ts
    add_story_to_stories_ts(article, story_slug, image_url, category, len(slides))

# =============================================================================
# CORE FUNCTIONS
# =============================================================================
def fetch_news_for_category(category: str) -> list:
    """Fetch news items from category RSS feeds."""
    news = []
    for url in CATEGORY_CONFIG[category]["feeds"]:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title = entry.get("title", "").strip()
                summary_raw = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r'<[^>]+>', '', summary_raw).strip()[:500]
                if title and len(title) > 20:
                    news.append({
                        "title": title, "summary": summary,
                        "link": entry.get("link", ""), "category": category
                    })
        except Exception as e:
            print(f"  Feed error ({url[:40]}): {e}")
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
            return model.generate_content(prompt).text
        except Exception as e:
            print(f"  [Gemini failed, trying Groq] {e}")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2500, "temperature": 0.7
        },
        timeout=90
    )
    return response.json()["choices"][0]["message"]["content"]

def generate_article(item: dict, category: str) -> Optional[dict]:
    """Generate article in CASUAL Hinglish (not shuddh Hindi)."""
    category_task = {
        "AI": "AI aur Technology news ke baare mein likhein.",
        "Deals": "Amazon/Flipkart ke best tech deal ke baare mein likhein. Actual price, original MRP, discount %, aur product ka link zaroor mention karein.",
        "Software": "Software update ya naye features ke baare mein likhein. Version number aur key changes clearly batayein.",
        "Crypto": "Cryptocurrency market news. Price levels, trend aur India ke investors ke liye kya matlab.",
        "Gadgets": "Naye smartphone launches, laptops, ya EV (Electric Vehicles) cars in India ke baare mein likhein. Key specs, features, battery, aur expected price zaroor highlight karein.",
    }

    prompt = f"""You are the expert writer for AITechNews.co.in — India's No.1 Hinglish tech news website.

News: "{item['title']}"
Context: {item['summary'][:400]}
Category: {category}
Task: {category_task.get(category, '')}

WRITING STYLE — exactly match these examples from our existing articles:
{HANGING_STYLE_EXAMPLE}

STRICT LANGUAGE RULES (violate = rejected):
1. Write the main body content in PERFECT DEVANAGARI HINDI (हिंदी लिपि).
   ✅ CORRECT: "यह बहुत ही बढ़िया स्मार्टफोन है।"
   ❌ WRONG (Roman Hindi): "Yeh bahut hi badhiya smartphone hai."
2. The ONLY English words you should use are technical terms. Do NOT translate technical terms into Hindi.
   Technical terms to keep in English: AI, CPU, GPU, RAM, Bitcoin, App, Download, Update, Deal, Price, Launch, Feature, Bug, Patch, Sale, Smartphone, Display.
   ✅ CORRECT: "Google ने अपना नया AI Mode लॉन्च कर दिया है।"
3. In headings and body, you can use conversational words like 'यार', 'भाई', 'तो', 'क्या' so it doesn't sound like a boring textbook, but it MUST be in Devanagari script.
4. Use **bold** for all English technical terms and important numbers/prices.
5. Write 500+ words. Use \\n\\n between paragraphs.
6. NEVER start with "इस आर्टिकल में" or "आज हम बात करेंगे" — start with an exciting hook!
7. The title/heading MUST be a mix of Devanagari and English with an emoji at the end. Example: "Google का नया AI Tool — Game Changer है या Hype? 🤔"

Return ONLY raw JSON (NO markdown, NO backticks, NO extra text):
{{"title":"Catchy title with emoji (हिंदी+English), max 90 chars","slug":"url-slug-english-only-lowercase-hyphens-no-special-chars","excerpt":"2-3 line Hindi SEO preview","content":"Full 500+ word article in Devanagari Hindi + English tech terms using \\n\\n between paragraphs","category":"{category}","readingTime":"5 min read"}}"""

    try:
        return parse_json_response(call_ai(prompt))
    except Exception as e:
        print(f"  Generation error: {e}")
        return None

def create_markdown(article: dict, today_formatted: str, image_url: str) -> str:
    title = article['title'].replace('"', "'").replace('\n', ' ')
    excerpt = article['excerpt'].replace('"', "'").replace('\n', ' ')
    return f"""---
title: "{title}"
date: "{today_formatted}"
category: "{article.get('category', 'AI')}"
excerpt: "{excerpt}"
image: "{image_url}"
readingTime: "{article.get('readingTime', '5 min read')}"
---

{article['content']}
"""

def generate_and_upload_hf_image(title: str, slug: str, category: str) -> str:
    image_style = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["AI"])["image_style"]
    if not HF_TOKEN:
        encoded = title.replace(" ", "%20")[:100]
        return f"https://image.pollinations.ai/prompt/{encoded}%20{image_style.replace(' ', '%20')}?width=1200&height=630&nologo=true"

    print("  Generating HF image via SDXL...")
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    prompt_text = f"hyperrealistic, cinematic lighting, 8k, masterpiece, {image_style}"
    for attempt in range(2):
        try:
            res = requests.post(API_URL, headers={"Authorization": f"Bearer {HF_TOKEN}"},
                                json={"inputs": prompt_text}, timeout=120)
            if res.status_code == 200 and len(res.content) > 5000:
                fname = f"{slug}.jpg"
                if push_file_to_github(f"{IMAGE_PATH}/{fname}", res.content, is_binary=True):
                    return f"/images/blog/{fname}"
        except Exception as e:
            print(f"  HF attempt {attempt+1}: {e}")
        time.sleep(10)

    print("  Falling back to Pollinations.")
    encoded = title.replace(" ", "%20")[:100]
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true"

def push_file_to_github(filepath: str, content, is_binary: bool = False) -> bool:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    sha = None
    check = requests.get(url, headers=headers)
    if check.status_code == 200:
        sha = check.json().get("sha")
    encoded_content = base64.b64encode(content).decode('ascii') if is_binary else base64.b64encode(content.encode('utf-8')).decode('ascii')
    payload = {"message": f"Auto: {filepath.split('/')[-1]}", "content": encoded_content, "branch": "main"}
    if sha:
        payload["sha"] = sha
    res = requests.put(url, headers=headers, json=payload)
    if res.status_code not in [200, 201]:
        print(f"  GitHub push failed ({res.status_code}): {res.text[:150]}")
        return False
    return True

def post_to_telegram(title: str, slug: str, image_url: str, category: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    article_url = f"https://aitechnews.co.in/blog/{slug}"
    chat_id = TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID.startswith(('@', '-')) else f"@{TELEGRAM_CHAT_ID}"
    hashtags = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["AI"])["hashtags"]
    emoji = CATEGORY_CONFIG.get(category, {}).get("emoji", "📰")
    caption = f"{emoji} *{title}*\n\n👉 [Full Article]({article_url})\n\n{hashtags}"
    photo_url = f"https://aitechnews.co.in{image_url}" if image_url.startswith("/") else image_url
    try:
        res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
            json={"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "Markdown"}, timeout=30)
        if res.status_code == 200:
            print("  ✓ Telegram")
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": f"{caption}\n\n{article_url}", "parse_mode": "Markdown"}, timeout=30)
            print("  ✓ Telegram (text)")
    except Exception as e:
        print(f"  ✗ Telegram: {e}")

def post_to_twitter(title: str, slug: str, category: str):
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        return
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY, consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET
        )
        article_url = f"https://aitechnews.co.in/blog/{slug}"
        hashtags = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["AI"])["hashtags"]
        max_len = 240 - len(article_url) - len(hashtags) - 4
        tweet = f"{title[:max_len]}\n\n{article_url}\n\n{hashtags}"
        client.create_tweet(text=tweet)
        print("  ✓ Twitter")
    except Exception as e:
        print(f"  ✗ Twitter: {e}")

def post_to_facebook(title: str, slug: str, image_url: str, category: str):
    if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
        return
    try:
        article_url = f"https://aitechnews.co.in/blog/{slug}"
        hashtags = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["AI"])["hashtags"]
        message = f"{title}\n\n{article_url}\n\n{hashtags}"
        photo_url = f"https://aitechnews.co.in{image_url}" if image_url.startswith("/") else image_url
        res = requests.post(f"https://graph.facebook.com/v22.0/{FB_PAGE_ID}/photos",
            data={"url": photo_url, "caption": message, "access_token": FB_PAGE_ACCESS_TOKEN}, timeout=30)
        if res.status_code == 200:
            print("  ✓ Facebook")
        else:
            requests.post(f"https://graph.facebook.com/v22.0/{FB_PAGE_ID}/feed",
                data={"message": message, "link": article_url, "access_token": FB_PAGE_ACCESS_TOKEN}, timeout=30)
            print("  ✓ Facebook (link post)")
    except Exception as e:
        print(f"  ✗ Facebook: {e}")

# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================
def publish_category(category: str, today_formatted: str, today_slug: str,
                     history: dict, published_titles: list) -> int:
    config = CATEGORY_CONFIG[category]
    count = config["count"]
    print(f"\n{'='*60}")
    print(f"  CATEGORY: {config['emoji']} {category} (target: {count} articles)")
    print(f"{'='*60}")

    news = fetch_news_for_category(category)
    if not news:
        print(f"  No news found. Skipping.")
        return 0

    published = 0
    for item in news:
        if published >= count:
            break
        if is_duplicate(item["title"], history):
            continue

        print(f"\n  [{published+1}/{count}] {item['title'][:65]}...")
        try:
            article = generate_article(item, category)
            if not article:
                print("  Skipping - generation failed")
                continue

            slug = re.sub(r'[^a-z0-9-]', '', article.get("slug", "tech-news").lower().replace(' ', '-'))[:50].strip('-')
            filename = f"{category.lower()}-{slug}-{today_slug}.md"
            image_url = generate_and_upload_hf_image(item['title'][:80], slug, category)
            md_content = create_markdown(article, today_formatted, image_url)

            if push_file_to_github(f"{CONTENT_PATH}/{filename}", md_content):
                published += 1
                published_titles.append(item["title"])
                print(f"  ✓ Published: {filename}")

                clean_slug = filename.replace('.md', '')
                article_url = f"https://aitechnews.co.in/blog/{clean_slug}"

                post_to_telegram(article['title'], clean_slug, image_url, category)
                post_to_twitter(article['title'], clean_slug, category)
                post_to_facebook(article['title'], clean_slug, image_url, category)
                publish_web_story(article, slug, image_url, category, article_url)

            time.sleep(10)

        except Exception as e:
            print(f"  Error: {e}")

    return published

def main():
    print("=" * 60)
    print("=== AITechNews Publisher v4.0 - ULTRA UPDATE ===")
    print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print("Fixes: Deduplication + Casual Hinglish + Web Stories + Amazon Deals")
    print("=" * 60)

    today_formatted = datetime.now(timezone.utc).strftime("%d %B %Y")
    today_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("\n📚 Loading published history for deduplication...")
    history = load_published_history()
    print(f"  Found {len(history.get('published', []))} recent articles in history")

    published_titles = []
    total = 0
    for category in CATEGORY_CONFIG:
        count = publish_category(category, today_formatted, today_slug, history, published_titles)
        total += count
        time.sleep(5)

    save_published_history(history, published_titles)

    print(f"\n{'='*60}")
    print(f"✅ DONE! {total}/12 articles published today!")
    print(f"📖 Deduplication: {len(published_titles)} titles tracked")
    print(f"📱 Web Stories: {total} new stories added")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
