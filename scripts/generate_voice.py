"""
Voice + subtitle generator using edge-tts.
Supports short hook index (0/1/2) for 3 distinct Shorts per day.
"""
import asyncio, json, os
import edge_tts

FULL_VOICE  = "en-US-GuyNeural"
SHORT_VOICE = "en-US-AriaNeural"
FULL_RATE   = "-5%"
SHORT_RATE  = "+5%"


async def _generate(text, voice, rate, audio_path, srt_path):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    words = []
    with open(audio_path, "wb") as af:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                af.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "word": chunk["text"],
                    "start_ms": chunk["offset"] // 10_000,
                    "duration_ms": chunk["duration"] // 10_000,
                })
    _write_srt(words, srt_path)
    _write_words(words, srt_path.replace(".srt","_words.json"))


def _write_srt(words, path):
    CHUNK = 6
    lines = []
    for i in range(0, len(words), CHUNK):
        chunk = words[i:i+CHUNK]
        if not chunk: continue
        s = chunk[0]["start_ms"]
        e = chunk[-1]["start_ms"] + chunk[-1]["duration_ms"]
        lines.append({"i": len(lines)+1, "s": _ts(s), "e": _ts(e),
                      "t": " ".join(w["word"] for w in chunk)})
    with open(path, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(f"{l['i']}\n{l['s']} --> {l['e']}\n{l['t']}\n\n")


def _write_words(words, path):
    with open(path, "w") as f: json.dump(words, f, indent=2)


def _ts(ms):
    h=ms//3_600_000; ms%=3_600_000
    m=ms//60_000; ms%=60_000
    s=ms//1_000; ms%=1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _run(text, voice, rate, audio, srt):
    asyncio.run(_generate(text, voice, rate, audio, srt))


def run(scripts):
    """Full pipeline — generates voice for long-form + short hook 0."""
    os.makedirs("output/audio", exist_ok=True)
    os.makedirs("output/subtitles", exist_ok=True)
    print("[1/2] Full video voiceover...")
    _run(scripts["full_script"], FULL_VOICE, FULL_RATE,
         "output/audio/full_voice.mp3", "output/subtitles/full.srt")
    print("[2/2] Short voiceover (hook 0)...")
    hook_idx = int(os.environ.get("SHORT_HOOK_INDEX","0"))
    hook_key = f"hook_{hook_idx}"
    hook_text = scripts["hooks"].get(hook_key, scripts["hooks"]["hook_0"])
    _run(hook_text, SHORT_VOICE, SHORT_RATE,
         "output/audio/short_voice.mp3", "output/subtitles/short.srt")
    return {
        "full_audio":  "output/audio/full_voice.mp3",
        "full_srt":    "output/subtitles/full.srt",
        "short_audio": "output/audio/short_voice.mp3",
        "short_srt":   "output/subtitles/short.srt",
        "hook_index":  hook_idx,
    }


def run_short_only(scripts):
    """Short pipeline — generates only the selected hook voiceover."""
    os.makedirs("output/audio", exist_ok=True)
    os.makedirs("output/subtitles", exist_ok=True)
    hook_idx = int(os.environ.get("SHORT_HOOK_INDEX","0"))
    hook_key = f"hook_{hook_idx}"
    hook_text = scripts["hooks"].get(hook_key, scripts["hooks"]["hook_0"])
    print(f"[1/1] Short voiceover (hook {hook_idx})...")
    _run(hook_text, SHORT_VOICE, SHORT_RATE,
         "output/audio/short_voice.mp3", "output/subtitles/short.srt")
    return {
        "short_audio": "output/audio/short_voice.mp3",
        "short_srt":   "output/subtitles/short.srt",
        "hook_index":  hook_idx,
    }
