"""
Script generator — calls Gemini API directly via requests (no SDK version issues).
"""
import os, json, random, requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"

FULL_PROMPT = """You are a professional true crime documentary scriptwriter.
Write in the style of MrBallen, Eleanor Neale, and Cayleigh Elise.

STRUCTURE (follow exactly):
1. HOOK (30s) — Most shocking fact first. No intro. No "welcome". Start mid-story.
2. BACKGROUND (2-3 min) — Humanise the people involved. Specific details.
3. TIMELINE (3-4 min) — Step by step. End every paragraph on a tension beat.
4. INVESTIGATION (2-3 min) — Police response, evidence, twists.
5. RESOLUTION — Outcome or open cliffhanger. Make viewers comment.

RULES:
- Max 18 words per sentence. Present tense. Short punchy beats.
- Use "Jane" or "the victim" — never real living victim names.
- Plain narration only — no markdown, no headers.
- Target 1200-1500 words (~8-10 min at 145 WPM).
"""

HOOKS_PROMPT = """You write viral 60-second hooks for YouTube Shorts.
Given a full true crime script, write THREE distinct hooks — each under 150 words.
Each hook targets a different emotional angle:
- Hook 0: The mystery angle — "Nobody knows what happened to..."
- Hook 1: The suspect angle — "Everyone trusted him. Nobody should have."
- Hook 2: The evidence angle — "One clue. Overlooked for 13 years."

Each hook must:
- Start with the most gripping sentence in the whole story
- Build tension across 4-5 punchy sentences
- End with an unanswered question that demands the full video
- NEVER resolve the case
- NO intros like "Today we cover..."

Return ONLY valid JSON — no markdown, no backticks:
{"hook_0": "...", "hook_1": "...", "hook_2": "..."}
"""

META_PROMPT = """You are a YouTube SEO and CTR expert for true crime channels.
Return ONLY valid JSON — no markdown, no backticks.

TITLE RULES (proven 8%+ CTR formulas):
- Keyword in first 5 words
- Use: "The [X] Nobody Could Explain", "She Vanished. Nobody Asked Questions.",
  "[Number] Clues Ignored For [X] Years", "What Really Happened To [Name]"
- Max 70 chars. Numbers + mystery words (vanished, hidden, unsolved, secret).

SHORT TITLE: max 40 chars, curiosity-gap format
TAGS: 15 tags — mix broad + specific + long-tail
DESCRIPTION line 1: most gripping sentence from the script
DESCRIPTION line 2: "New true crime documentary every day — subscribe so you never miss a case."
Then: 3-sentence keyword-rich summary + #TrueCrime #Mystery #ColdCase #Documentary

Return JSON with keys: youtube_title, youtube_description, youtube_tags (list),
short_title, short_description, primary_keyword
"""


def _call(prompt: str, max_tokens: int = 4096) -> str:
    """Call Gemini API directly via REST — no SDK needed."""
    key = os.environ["GEMINI_API_KEY"]
    url = f"{GEMINI_URL}?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.8},
    }
    resp = requests.post(url, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def load_topics(path="topics.txt"):
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def pick_topic(topics, used_path="logs/used_topics.json"):
    os.makedirs("logs", exist_ok=True)
    try:
        with open(used_path) as f: used = set(json.load(f))
    except FileNotFoundError: used = set()
    available = [t for t in topics if t not in used]
    if not available: used = set(); available = topics
    topic = random.choice(available)
    used.add(topic)
    with open(used_path, "w") as f: json.dump(list(used), f)
    return topic


def run(topics_file="topics.txt"):
    print("[1/4] Picking topic...")
    topics = load_topics(topics_file)
    topic = pick_topic(topics)
    print(f"      Topic: {topic}")

    print("[2/4] Generating full documentary script...")
    full_script = _call(f"{FULL_PROMPT}\n\nWrite a full script about: {topic}", max_tokens=4096)
    print(f"      Words: {len(full_script.split())}")

    print("[3/4] Generating 3 short hooks...")
    hooks_raw = _call(f"{HOOKS_PROMPT}\n\nFull script:\n{full_script[:3000]}", max_tokens=1024)
    hooks_raw = hooks_raw.replace("```json","").replace("```","").strip()
    hooks = json.loads(hooks_raw)
    print(f"      Hooks generated: {list(hooks.keys())}")

    print("[4/4] Generating CTR-optimised metadata...")
    meta_raw = _call(
        f"{META_PROMPT}\n\nTopic: {topic}\nScript opening: {full_script[:400]}\nHook 0: {hooks['hook_0'][:120]}",
        max_tokens=1024,
    )
    meta_raw = meta_raw.replace("```json","").replace("```","").strip()
    metadata = json.loads(meta_raw)
    print(f"      Title: {metadata.get('youtube_title')}")

    result = {
        "topic": topic,
        "full_script": full_script,
        "hooks": hooks,
        "metadata": metadata,
    }
    os.makedirs("output", exist_ok=True)
    with open("output/scripts.json", "w") as f:
        json.dump(result, f, indent=2)
    return result
