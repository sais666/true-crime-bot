import json
import os
import subprocess
import random


# Output resolutions
FULL_W, FULL_H = 1920, 1080   # 16:9 YouTube
SHORT_W, SHORT_H = 1080, 1920  # 9:16 Shorts / TikTok / Reels

# Subtitle style — burned into video
FULL_SUB_STYLE = (
    "FontName=Arial,"
    "FontSize=36,"
    "PrimaryColour=&HFFFFFF,"
    "OutlineColour=&H000000,"
    "BorderStyle=3,"
    "Outline=2,"
    "Shadow=1,"
    "Alignment=2,"          # bottom-center for 16:9
    "MarginV=60"
)

SHORT_SUB_STYLE = (
    "FontName=Arial,"
    "FontSize=44,"
    "PrimaryColour=&HFFFFFF,"
    "OutlineColour=&H000000,"
    "BorderStyle=3,"
    "Outline=2,"
    "Shadow=1,"
    "Alignment=5,"          # center for 9:16
    "MarginV=0"
)


def _run_ffmpeg(cmd: list[str], label: str) -> None:
    print(f"      Running FFmpeg: {label}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"      FFmpeg stderr:\n{result.stderr[-2000:]}")
        raise RuntimeError(f"FFmpeg failed: {label}")


def _build_video_inputs(clips: list[str], target_duration: float, w: int, h: int) -> str:
    """
    Write a concat list file and return its path.
    Loops clips if there aren't enough to fill the duration.
    """
    total = 0.0
    ordered = []
    random.shuffle(clips)

    while total < target_duration:
        for clip in clips:
            ordered.append(clip)
            total += 5.0   # estimate; ffprobe would be more accurate
            if total >= target_duration:
                break

    concat_path = "output/concat_list.txt"
    with open(concat_path, "w") as f:
        for clip in ordered:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    return concat_path


def _get_audio_duration(audio_path: str) -> float:
    """Use ffprobe to get audio duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 60.0   # fallback


def render_full_video(
    clips: list[str],
    audio_path: str,
    srt_path: str,
    output_path: str,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    duration = _get_audio_duration(audio_path)
    print(f"      Full video duration: {duration:.1f}s")

    concat = _build_video_inputs(clips, duration, FULL_W, FULL_H)
    abs_srt = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
    abs_srt_escaped = abs_srt.replace("'", "\\'")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat,  # video clips
        "-i", audio_path,                              # voiceover
        "-filter_complex",
        (
            f"[0:v]scale={FULL_W}:{FULL_H}:force_original_aspect_ratio=decrease,"
            f"pad={FULL_W}:{FULL_H}:(ow-iw)/2:(oh-ih)/2:black,"
            f"subtitles='{abs_srt_escaped}':force_style='{FULL_SUB_STYLE}'[v]"
        ),
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-t", str(duration),
        output_path,
    ]
    _run_ffmpeg(cmd, "full video")
    print(f"      Rendered: {output_path}")
    return output_path


def render_short_video(
    clips: list[str],
    audio_path: str,
    srt_path: str,
    output_path: str,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    duration = _get_audio_duration(audio_path)
    duration = min(duration, 60.0)   # shorts max 60s
    print(f"      Short duration: {duration:.1f}s")

    concat = _build_video_inputs(clips, duration, SHORT_W, SHORT_H)
    abs_srt = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
    abs_srt_escaped = abs_srt.replace("'", "\\'")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat,
        "-i", audio_path,
        "-filter_complex",
        (
            # Crop to 9:16 center crop, then burn subtitles in the center
            f"[0:v]scale={SHORT_W}:{SHORT_H}:force_original_aspect_ratio=increase,"
            f"crop={SHORT_W}:{SHORT_H},"
            f"subtitles='{abs_srt_escaped}':force_style='{SHORT_SUB_STYLE}'[v]"
        ),
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-t", str(duration),
        output_path,
    ]
    _run_ffmpeg(cmd, "short video")
    print(f"      Rendered: {output_path}")
    return output_path


def run(voice_files: dict, visual_files: dict) -> dict:
    print("[1/2] Rendering full 16:9 video...")
    full_video = render_full_video(
        clips=visual_files["full_clips"],
        audio_path=voice_files["full_audio"],
        srt_path=voice_files["full_srt"],
        output_path="output/rendered/full_video.mp4",
    )

    print("[2/2] Rendering 9:16 short...")
    short_video = render_short_video(
        clips=visual_files["short_clips"],
        audio_path=voice_files["short_audio"],
        srt_path=voice_files["short_srt"],
        output_path="output/rendered/short_video.mp4",
    )

    result = {
        "full_video": full_video,
        "short_video": short_video,
    }

    with open("output/rendered.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    with open("output/voice.json") as f:
        voice_files = json.load(f)
    with open("output/visuals.json") as f:
        visual_files = json.load(f)
    run(voice_files, visual_files)


def run_short_only(voice_files: dict, visual_files: dict) -> dict:
    """Short pipeline path — only render the 9:16 short."""
    print("[1/1] Rendering 9:16 short...")
    short_video = render_short_video(
        clips=visual_files["short_clips"],
        audio_path=voice_files["short_audio"],
        srt_path=voice_files["short_srt"],
        output_path="output/rendered/short_video.mp4",
    )
    result = {"short_video": short_video, "full_video": None}
    with open("output/rendered.json", "w") as f:
        json.dump(result, f, indent=2)
    return result
