import os
import json
import re
import time
import requests


PEXELS_API = "https://api.pexels.com/videos/search"
PEXELS_PHOTO_API = "https://api.pexels.com/v1/search"

# True crime keyword bank — matched to script sections
KEYWORD_BANK = {
    "hook": ["dark forest night", "abandoned house", "crime scene tape", "detective"],
    "background": ["old newspaper", "small town street", "vintage photograph", "courthouse"],
    "timeline": ["calendar pages", "clock ticking", "newspaper headlines", "city night"],
    "investigation": ["detective office", "police station", "fingerprints", "evidence"],
    "suspect": ["shadowy figure", "surveillance camera", "dark alley", "handcuffs"],
    "resolution": ["courtroom", "prison bars", "justice scales", "sunset hope"],
    "default": ["dark mystery", "night city", "fog street", "abandoned building"],
}

HEADERS = {}   # set in run()


def _search_videos(keyword: str, count: int = 3) -> list[dict]:
    """Search Pexels for video clips matching a keyword."""
    resp = requests.get(
        PEXELS_API,
        headers=HEADERS,
        params={"query": keyword, "per_page": count, "size": "medium"},
        timeout=15,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos", [])

    results = []
    for v in videos:
        # Pick the HD file (720p or 1080p)
        files = sorted(v.get("video_files", []), key=lambda x: x.get("height", 0), reverse=True)
        hd_files = [f for f in files if f.get("height", 0) >= 720]
        if hd_files:
            results.append({
                "id": v["id"],
                "url": hd_files[0]["link"],
                "width": hd_files[0]["width"],
                "height": hd_files[0]["height"],
                "duration": v["duration"],
                "keyword": keyword,
            })
    return results


def _download_video(url: str, dest: str) -> bool:
    """Download a video file to disk."""
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"      Warning: failed to download {url}: {e}")
        return False


def _extract_keywords_from_script(script: str) -> list[str]:
    """Pull section keywords based on script structure."""
    lower = script.lower()
    keywords = []

    # Map script content to keyword categories
    if any(w in lower for w in ["vanished", "disappeared", "missing", "never seen"]):
        keywords += KEYWORD_BANK["hook"]
    if any(w in lower for w in ["grew up", "born", "childhood", "family", "neighbors"]):
        keywords += KEYWORD_BANK["background"]
    if any(w in lower for w in ["night", "morning", "day", "week", "month", "year"]):
        keywords += KEYWORD_BANK["timeline"]
    if any(w in lower for w in ["detective", "police", "investigation", "evidence", "forensic"]):
        keywords += KEYWORD_BANK["investigation"]
    if any(w in lower for w in ["suspect", "arrested", "charged", "guilty", "person of interest"]):
        keywords += KEYWORD_BANK["suspect"]
    if any(w in lower for w in ["convicted", "sentenced", "verdict", "justice", "solved"]):
        keywords += KEYWORD_BANK["resolution"]

    # Always add some default atmospheric clips
    keywords += KEYWORD_BANK["default"]

    # Deduplicate and limit
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)

    return unique[:8]   # max 8 keyword searches


def fetch_visuals(script: str, output_dir: str, count_per_keyword: int = 2) -> list[str]:
    """Fetch and download stock footage. Returns list of local file paths."""
    os.makedirs(output_dir, exist_ok=True)

    keywords = _extract_keywords_from_script(script)
    print(f"      Keywords: {keywords}")

    downloaded = []
    for i, keyword in enumerate(keywords):
        print(f"      Fetching: '{keyword}'...")
        try:
            videos = _search_videos(keyword, count=count_per_keyword)
            for j, video in enumerate(videos):
                filename = f"{output_dir}/clip_{i:02d}_{j:02d}_{keyword.replace(' ', '_')}.mp4"
                if _download_video(video["url"], filename):
                    downloaded.append(filename)
                    print(f"        Saved: {filename}")
            time.sleep(0.5)   # be polite to the API
        except Exception as e:
            print(f"      Warning: failed keyword '{keyword}': {e}")

    return downloaded


def run(scripts: dict) -> dict:
    global HEADERS
    HEADERS = {"Authorization": os.environ["PEXELS_API_KEY"]}

    print("[1/2] Fetching visuals for full video...")
    full_clips = fetch_visuals(
        scripts["full_script"],
        output_dir="output/visuals/full",
        count_per_keyword=2,
    )
    print(f"      Downloaded {len(full_clips)} clips for full video")

    print("[2/2] Fetching visuals for short...")
    short_clips = fetch_visuals(
        scripts["hooks"]["hook_0"],
        output_dir="output/visuals/short",
        count_per_keyword=2,
    )
    print(f"      Downloaded {len(short_clips)} clips for short")

    result = {
        "full_clips": full_clips,
        "short_clips": short_clips,
    }

    with open("output/visuals.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    with open("output/scripts.json") as f:
        scripts = json.load(f)
    run(scripts)


def run_short_only(scripts: dict) -> dict:
    """Short pipeline path — only fetch visuals for the short."""
    global HEADERS
    HEADERS = {"Authorization": os.environ["PEXELS_API_KEY"]}

    print("[1/1] Fetching visuals for short...")
    short_clips = fetch_visuals(
        scripts["hooks"]["hook_0"],
        output_dir="output/visuals/short",
        count_per_keyword=2,
    )
    print(f"      Downloaded {len(short_clips)} clips for short")

    result = {"short_clips": short_clips, "full_clips": []}
    with open("output/visuals.json", "w") as f:
        json.dump(result, f, indent=2)

    return result
