"""
YouTube uploader — uploads video/short + auto-generates and uploads thumbnail.
"""
import os, json, requests
import generate_thumbnail as thumb_gen

TOKEN_URL  = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def _refresh_token():
    r = requests.post(TOKEN_URL, data={
        "client_id":     os.environ["YOUTUBE_CLIENT_ID"],
        "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    }, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def _upload(token, path, title, description, tags, privacy="public"):
    meta = {
        "snippet": {"title": title, "description": description,
                    "tags": tags, "categoryId": "22"},
        "status":  {"privacyStatus": privacy, "madeForKids": False},
    }
    init = requests.post(
        UPLOAD_URL,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "X-Upload-Content-Type": "video/mp4"},
        params={"uploadType": "resumable", "part": "snippet,status"},
        json=meta, timeout=30,
    )
    init.raise_for_status()
    up_url = init.headers["Location"]
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        r = requests.put(up_url,
            headers={"Content-Length": str(size), "Content-Type": "video/mp4"},
            data=f, timeout=600)
    r.raise_for_status()
    return r.json()["id"]


def run(rendered, scripts):
    meta   = scripts["metadata"]
    token  = _refresh_token()
    result = {}

    # ── Thumbnail (shared for both formats) ───────────────────
    thumb_path = thumb_gen.generate_thumbnail(
        title=meta.get("youtube_title", scripts["topic"]),
        script_text=scripts.get("full_script",""),
    )

    # ── Long-form ─────────────────────────────────────────────
    if rendered.get("full_video"):
        print("[1/2] Uploading long-form video...")
        vid_id = _upload(token, rendered["full_video"],
                         meta["youtube_title"],
                         meta["youtube_description"],
                         meta["youtube_tags"])
        result["youtube_video_id"]  = vid_id
        result["youtube_video_url"] = f"https://youtube.com/watch?v={vid_id}"
        print(f"      Live: {result['youtube_video_url']}")
        thumb_gen.upload_thumbnail(vid_id, thumb_path, token)

    # ── Short ─────────────────────────────────────────────────
    if rendered.get("short_video"):
        hook_idx = rendered.get("hook_index", 0)
        short_tags = meta["youtube_tags"] + ["Shorts","TrueCrimeShorts","YouTubeShorts"]
        print(f"[2/2] Uploading Short (hook {hook_idx})...")
        short_id = _upload(token, rendered["short_video"],
                           f"{meta['short_title']} #Shorts",
                           meta["short_description"], short_tags)
        result["youtube_short_id"]  = short_id
        result["youtube_short_url"] = f"https://youtube.com/shorts/{short_id}"
        print(f"      Live: {result['youtube_short_url']}")
        thumb_gen.upload_thumbnail(short_id, thumb_path, token)

    with open("output/youtube_upload.json","w") as f: json.dump(result, f, indent=2)
    return result


def run_short_only(rendered, scripts):
    meta     = scripts["metadata"]
    token    = _refresh_token()
    hook_idx = rendered.get("hook_index", 0)

    thumb_path = thumb_gen.generate_thumbnail(
        title=meta.get("short_title", scripts["topic"]),
        script_text=scripts.get("full_script",""),
    )

    short_tags = meta["youtube_tags"] + ["Shorts","TrueCrimeShorts","YouTubeShorts"]
    print(f"[1/1] Uploading Short (hook {hook_idx})...")
    short_id = _upload(token, rendered["short_video"],
                       f"{meta['short_title']} #Shorts",
                       meta["short_description"], short_tags)
    result = {
        "youtube_short_id":  short_id,
        "youtube_short_url": f"https://youtube.com/shorts/{short_id}",
    }
    print(f"      Live: {result['youtube_short_url']}")
    thumb_gen.upload_thumbnail(short_id, thumb_path, token)
    with open("output/youtube_upload.json","w") as f: json.dump(result, f, indent=2)
    return result
