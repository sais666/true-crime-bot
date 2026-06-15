# True Crime Bot — Free Cloud Pipeline

Fully automated true crime YouTube channel. Runs entirely in the cloud via GitHub Actions.
Generates a script, voiceover, subtitles, and video — then uploads to YouTube, TikTok, and Instagram Reels.
No laptop required. 100% free.

---

## What it does

Every Monday, Wednesday, and Friday at 10:00 AM UTC it automatically:

1. Picks a topic from `topics.txt`
2. Writes a full script + short hook using the Claude API
3. Generates voiceover with `edge-tts` (Microsoft Neural voices)
4. Creates word-synced `.SRT` subtitles
5. Downloads keyword-matched stock footage from Pexels
6. Renders a **16:9 full video** (YouTube) and a **9:16 short** (TikTok/Reels/Shorts)
7. Uploads both to YouTube via the official Data API
8. Uploads the short to TikTok and Instagram via browser automation

---

## Setup — Step by Step

### 1. Fork this repo

Click **Fork** on GitHub. Keep it public to get unlimited GitHub Actions minutes.

---

### 2. Get your API keys

#### Anthropic (Claude API)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Free tier works for 1 script per run

#### Pexels API
1. Go to [pexels.com/api](https://www.pexels.com/api/)
2. Sign up and get a free API key
3. 200 requests/hour — more than enough

#### YouTube Data API v3
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable **YouTube Data API v3**
3. Create **OAuth 2.0 credentials** (Desktop app type)
4. Download the `client_secret.json` file
5. Run this once on your laptop to get a refresh token:

```bash
pip install google-auth-oauthlib
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    scopes=['https://www.googleapis.com/auth/youtube.upload']
)
creds = flow.run_local_server(port=0)
print('REFRESH TOKEN:', creds.refresh_token)
print('CLIENT ID:', creds.client_id)
print('CLIENT SECRET:', creds.client_secret)
"
```

---

### 3. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add each of these:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `PEXELS_API_KEY` | Your Pexels API key |
| `YOUTUBE_CLIENT_ID` | From the OAuth step above |
| `YOUTUBE_CLIENT_SECRET` | From the OAuth step above |
| `YOUTUBE_REFRESH_TOKEN` | From the OAuth step above |
| `TIKTOK_EMAIL` | Your TikTok login email |
| `TIKTOK_PASSWORD` | Your TikTok password |
| `INSTAGRAM_EMAIL` | Your Instagram login email |
| `INSTAGRAM_PASSWORD` | Your Instagram password |

---

### 4. Customize your topics

Edit `topics.txt` — one topic per line. The bot picks one per run and never repeats until all are used.

---

### 5. Test it manually

Go to **Actions tab** → **True Crime Bot Pipeline** → **Run workflow**

Watch the logs in real time. Your first video will be live within ~15 minutes.

---

## Changing the schedule

Edit `.github/workflows/pipeline.yml`:

```yaml
- cron: '0 10 * * 1,3,5'   # Mon, Wed, Fri at 10 AM UTC
```

Use [crontab.guru](https://crontab.guru) to build your own schedule.

---

## Changing the voice

Edit `scripts/generate_voice.py`:

```python
FULL_VOICE = "en-US-GuyNeural"    # deep male voice
SHORT_VOICE = "en-US-AriaNeural"  # female voice
```

Available free voices: `en-US-GuyNeural`, `en-US-AriaNeural`, `en-US-JennyNeural`,
`en-GB-RyanNeural`, `en-AU-NatashaNeural`

---

## File structure

```
true-crime-bot/
├── .github/workflows/
│   └── pipeline.yml          # cloud scheduler
├── scripts/
│   ├── main.py               # orchestrator
│   ├── generate_script.py    # Claude API
│   ├── generate_voice.py     # edge-tts
│   ├── fetch_visuals.py      # Pexels API
│   ├── render_video.py       # FFmpeg
│   ├── upload_youtube.py     # YouTube Data API
│   └── upload_social.py      # Playwright (TikTok + Instagram)
├── topics.txt                # your case list
├── requirements.txt
└── README.md
```

---

## Free tier limits

| Service | Limit | Impact |
|---|---|---|
| GitHub Actions | 2,000 min/mo (private) · unlimited (public) | Fine for 3x/week |
| Claude API | Rate limited on free tier | Fine for 1 script/run |
| Pexels API | 200 req/hr | Fine for all clips |
| Google Drive | 15 GB | Delete after upload |

---

## Important notes

- Keep the repo **public** for unlimited GitHub Actions minutes
- Push a commit at least every 60 days to keep scheduled workflows active
- TikTok and Instagram uploads use browser automation — if the UI changes, selectors may need updating
- Never commit API keys directly — always use GitHub Secrets
