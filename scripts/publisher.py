#!/usr/bin/env python3
import os, json, feedparser, requests, re, time, base64
from datetime import datetime, timezone

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GH_TOKEN = os.environ.get("AITECHINDIA_TOKEN", "")
REPO = "Yoginogia/aitechindia"
PATH = "src/content/blog"

RSS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/ai/feed/",
    "https://blog.google/technology/ai/rss/",
    "https://openai.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
]

IMAGES = [
    "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=800&q=80",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&q=80",
    "https://images.unsplash.com/photo-1655720828018-edd2daec9349?w=800&q=80",
]

def fetch():
    news = []
    for url in RSS:
        try:
            for e in feedparser.parse(url).entries[:4]:
                t = e.get("title","").strip()
                s = re.sub(r'<[^>]+>','',e.get("summary",e.get("description","")).strip())[:300]
                if t and len(t)>20:
                    news.append({"title":t,"summary":s,"link":e.get("link","")})
        except: pass
    print(f"Fetched: {len(news)}")
    return news

def groq(prompt, tokens=1000):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
        json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"max_tokens":tokens},
        timeout=60)
    return r.json()["choices"][0]["message"]["content"]

def push(filename, content):
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}/{filename}"
    h = {"Authorization":f"token {GH_TOKEN}","Accept":"application/vnd.github.v3+json"}
    sha = None
    c = requests.get(url,headers=h)
    if c.status_code==200: sha=c.json().get("sha")
    p = {"message":f"Auto: {filename}","content":base64.b64encode(content.encode()).decode(),"branch":"main"}
    if sha: p["sha"]=sha
    r = requests.put(url,headers=h,json=p)
    ok = r.status_code in [200,201]
    print(f"  {'PUSHED' if ok else 'FAILED'}: {filename} ({r.status_code})")
    return ok

def main():
    print("=== AITechNews Publisher ===")
    news = fetch()
    if not news: return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = int(os.environ.get("ARTICLES_COUNT","3"))
    published = 0

    for i, item in enumerate(news[:count]):
        print(f"\nWriting article {i+1}: {item['title'][:50]}")
        try:
            resp = groq(f"""Write a 400-word Hinglish tech article for AITechNews.co.in about:
"{item['title']}"
Summary: {item['summary']}

Respond ONLY with JSON (no backticks):
{{"title":"Hinglish title","slug":"url-slug","excerpt":"2 line preview","content":"full article with \\n\\n paragraphs","category":"AI News","readingTime":"3 min read"}}""", 1500)
            clean = re.sub(r'```json|```','',resp).strip()
            art = json.loads(clean[clean.find('{'):clean.rfind('}')+1])
            slug = re.sub(r'[^a-z0-9-]','',art.get("slug","ai-news").lower())[:50]
            filename = f"{slug}-{today}.md"
            md = f"""---
title: "{art['title'].replace('"',"'")}"
date: {today}
category: {art.get('category','AI News')}
excerpt: "{art['excerpt'].replace('"',"'")}"
image: {IMAGES[i%len(IMAGES)]}
readingTime: {art.get('readingTime','3 min read')}
---

{art['content']}
"""
            if push(filename, md):
                published += 1
            time.sleep(4)
        except Exception as e:
            print(f"  Error: {e}")

    print(f"\nDone! {published} articles published to aitechindia!")

if __name__ == "__main__":
    main()
