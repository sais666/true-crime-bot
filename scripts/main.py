"""
Orchestrator — reads PIPELINE_MODE (short/long) and SHORT_HOOK_INDEX (0/1/2).
3 short runs per day + 1 long run = 4 total uploads daily.
"""
import json, os, sys, traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import generate_script, generate_voice, fetch_visuals, render_video, upload_youtube

LOG = "logs/pipeline.log"


def log(msg):
    ts   = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs("logs", exist_ok=True)
    with open(LOG, "a") as f: f.write(line + "\n")


def run_short(scripts):
    log("STEP 2 — Voice (edge-tts)")
    voice = generate_voice.run_short_only(scripts)

    log("STEP 3 — Stock footage (Pexels)")
    visuals = fetch_visuals.run_short_only(scripts)
    if not visuals["short_clips"]: raise RuntimeError("No clips — check PEXELS_API_KEY")

    log("STEP 4 — Render 9:16 Short (FFmpeg)")
    rendered = render_video.run_short_only(voice, visuals)
    rendered["hook_index"] = voice.get("hook_index", 0)

    log("STEP 5 — Upload to YouTube Shorts + thumbnail")
    return upload_youtube.run_short_only(rendered, scripts)


def run_long(scripts):
    log("STEP 2 — Voice (edge-tts)")
    voice = generate_voice.run(scripts)

    log("STEP 3 — Stock footage (Pexels)")
    visuals = fetch_visuals.run(scripts)
    if not visuals["full_clips"]: raise RuntimeError("No clips — check PEXELS_API_KEY")

    log("STEP 4 — Render 16:9 video + 9:16 Short (FFmpeg)")
    rendered = render_video.run(voice, visuals)
    rendered["hook_index"] = voice.get("hook_index", 0)

    log("STEP 5 — Upload to YouTube + thumbnail")
    return upload_youtube.run(rendered, scripts)


def run_pipeline():
    mode      = os.environ.get("PIPELINE_MODE","long").strip().lower()
    hook_idx  = os.environ.get("SHORT_HOOK_INDEX","0")
    start     = datetime.utcnow()

    log("=" * 60)
    log(f"Pipeline start — mode: {mode.upper()} | hook: {hook_idx}")

    try:
        log("STEP 1 — Script + hooks + metadata (Gemini)")
        scripts = generate_script.run("topics.txt")
        log(f"  Topic: {scripts['topic']}")
        log(f"  Title: {scripts['metadata'].get('youtube_title')}")
        log(f"  Keyword: {scripts['metadata'].get('primary_keyword')}")

        results = run_short(scripts) if mode == "short" else run_long(scripts)

        duration = (datetime.utcnow() - start).seconds
        log(f"Done in {duration}s")
        for k,v in results.items(): log(f"  {k}: {v}")

        os.makedirs("output", exist_ok=True)
        with open("output/run_summary.json","w") as f:
            json.dump({"mode":mode,"hook":hook_idx,"topic":scripts["topic"],
                       "duration":duration,"results":results}, f, indent=2)
        log("=" * 60)

    except Exception as e:
        log(f"FAILED: {e}")
        log(traceback.format_exc())
        log("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
