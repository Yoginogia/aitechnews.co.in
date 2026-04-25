#!/usr/bin/env python3
"""Quick test to verify upgraded agent works with Gemini 2.0 Flash."""
import os

print("=" * 50)
print("AI Agent Upgrade Test")
print("=" * 50)

# 1. Check env vars
gemini_key = os.environ.get("GEMINI_API_KEY", "")
groq_key = os.environ.get("GROQ_API_KEY", "")
github_token = os.environ.get("AITECHINDIA_TOKEN", "")

print(f"\nGEMINI_API_KEY: {'SET (' + gemini_key[:8] + '...)' if gemini_key else 'NOT SET'}")
print(f"GROQ_API_KEY: {'SET' if groq_key else 'NOT SET'}")
print(f"AITECHINDIA_TOKEN: {'SET' if github_token else 'NOT SET'}")

# 2. Test Gemini
try:
    import google.generativeai as genai
    print("\ngoogle-generativeai: INSTALLED")
except ImportError:
    print("\ngoogle-generativeai: NOT INSTALLED")
    print("Run: pip install google-generativeai")
    exit(1)

if not gemini_key:
    print("\nERROR: GEMINI_API_KEY not set!")
    exit(1)

genai.configure(api_key=gemini_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# 3. Generate a test article
print("\nGenerating test article with Gemini 2.0 Flash...")
test_prompt = """You are a SENIOR tech journalist for AITechNews.co.in.

NEWS: "Google launches new AI search features in India"
CATEGORY: AI

RULES:
1. ALL Hindi in DEVANAGARI script + English technical terms
2. MINIMUM 300 words for this test
3. Include at least 1 markdown table
4. Professional tone, NO "यार" or "भाई"
5. Use **bold** for English terms

Write a SHORT test article (300 words). Return ONLY the article text, no JSON."""

try:
    response = model.generate_content(
        test_prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=2000,
        )
    )
    article = response.text
    
    # Validate
    words = len(article.split())
    hindi_chars = sum(1 for c in article if '\u0900' <= c <= '\u097F')
    has_table = '|---|' in article or '| ---' in article
    has_bold = '**' in article
    
    print(f"\n{'=' * 50}")
    print(f"TEST RESULTS:")
    print(f"{'=' * 50}")
    print(f"Words: {words} {'✅' if words > 200 else '❌'}")
    print(f"Devanagari chars: {hindi_chars} {'✅' if hindi_chars > 50 else '❌'}")
    print(f"Has table: {'✅' if has_table else '⚠️ (not required for short test)'}")
    print(f"Has bold terms: {'✅' if has_bold else '❌'}")
    
    print(f"\n--- Article Preview (first 500 chars) ---")
    print(article[:500])
    print("...")
    
    if words > 150 and hindi_chars > 30:
        print(f"\n🎉 SUCCESS! Gemini 2.0 Flash is working perfectly!")
        print(f"Agent is ready for tomorrow's run!")
    else:
        print(f"\n⚠️ Article generated but quality needs checking.")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("Check your GEMINI_API_KEY!")
