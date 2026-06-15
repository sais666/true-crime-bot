"""
Script generator — Gemini API
Produces: full documentary script, 3 distinct short hooks, CTR-optimised metadata
"""
import os, json, random
import google.generativeai as genai


FULL_PROMPT = """You are a professional true crime documentary scriptwriter.
Write in the style of MrBallen, Eleanor Neale, and Cayleigh Elise.

STRUCTURE (follow exactly):
1. HOOK (30s) — Most shocking fact first. No intro. No "welcome". Start mid-story.
2. BACKGROUND (2–3 min) — Humanise the people involved. Specific details.
3. TIMELINE (3–4 min) — Step by step. End every paragraph on a tension beat.
4. INVESTIGATION (2–3 min) — Police response, evidence, twists.
5. RESOLUTION — Outcome or open cliffhanger. Make viewers comment.

RULES:
- Max 18 words per sentence. Present tense. Short punchy beats.
- Use "Jane" or "the victim" — never real living victim names.
- Plain narration only — no markdown, no headers.
- Target 1,200–1,500 words (~8–10 min at 145 WPM).
"""

HOOKS_PROMPT = """You write viral 60-second hooks for YouTube Shorts.
Given a full true crime script, write THREE distinct hooks — each under 150 words.
Each hook targets a different emotional angle:
- Hook 0: The mystery angle — "Nobody knows what happened to..."
- Hook 1: The suspect angle — "Everyone trusted him. Nobody should have."
- Hook 2: The evidence angle — "One clue. Overlooked for 13 years."

Each hook must:
- Start with the most gripping sentence in the whole story
- Build tension across 4–5 punchy sentences
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

SHORT TITLE: max 40 chars, curiosity-gap format, no period at end
TAGS: 15 tags — mix broad (true crime, mystery, documentary) + specific (cold case 2025, unsolved murder documentary) + long-tail
DESCRIPTION line 1: the most gripping sentence from the script
DESCRIPTION line 2: "New true crime documentary every day — subscribe so you never miss a case."
Then: 3-sentence keyword-rich summary + #TrueCrime #Mystery #ColdCase #Documentary

Return JSON with keys: youtube_title, youtube_description, youtube_tags (list),
short_title, short_description, primary_keyword
"""


def _model():
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    return genai.GenerativeModel("gemini-2.0-flash")


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


def generate_full_script(topic):
    m = _model()
    r = m.generate_content(f"{FULL_PROMPT}\n\nWrite a full script about: {topic}")
    return r.text.strip()


def generate_hooks(full_script):
    m = _model()
    r = m.generate_content(f"{HOOKS_PROMPT}\n\nFull script:\n{full_script[:3000]}")
    raw = r.text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)


def generate_metadata(topic, full_script, hooks):
    m = _model()
    prompt = (
        f"{META_PROMPT}\n\n"
        f"Topic: {topic}\n"
        f"Script opening (400 chars): {full_script[:400]}\n"
        f"Hook 0 preview: {hooks['hook_0'][:120]}"
    )
    r = m.generate_content(prompt)
    raw = r.text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)


def run(topics_file="topics.txt"):
    print("[1/4] Picking topic...")
    topics = load_topics(topics_file)
    topic = pick_topic(topics)
    print(f"      Topic: {topic}")

    print("[2/4] Generating full documentary script...")
    full_script = generate_full_script(topic)
    print(f"      Words: {len(full_script.split())}")

    print("[3/4] Generating 3 short hooks...")
    hooks = generate_hooks(full_script)
    for i, k in enumerate(["hook_0","hook_1","hook_2"]):
        print(f"      Hook {i}: {len(hooks[k].split())} words")

    print("[4/4] Generating CTR-optimised metadata...")
    metadata = generate_metadata(topic, full_script, hooks)
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
