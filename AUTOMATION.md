# Automation — what is built vs what is not

## Short answer

**No tool can fully automate a free Faceless Instagram channel end-to-end** without paid APIs or breaking platform rules.

This project automates the **production draft**. You still upload to Instagram (unless you add official Meta credentials later).

## Multi-model LLM support

Providers: `offline` | `gemini` | `groq` | `openrouter` | `openai` | `auto`

Copy [`.env.example`](.env.example) → `.env` and fill keys. See [`RESOURCES.md`](RESOURCES.md).

```bat
python -m automation --niche "forgotten Indian history" --provider gemini --model gemini-3.1-pro-preview --tts local
python -m automation --niche "forgotten Indian history" --provider groq --tts local
python -m automation --niche "forgotten Indian history" --provider openrouter --tts local
python -m automation --niche "forgotten Indian history" --provider auto --tts local
```

`--mode` is an alias for `--provider`.

| Feature | Flag | Free tier? |
|---|---|---|
| Scripts via Gemini/Groq/OpenRouter | `--provider …` | Usually yes (limits apply) |
| Gemini Pro quality | `--provider gemini --model gemini-3.1-pro-preview` | If AI Studio project allows that model |
| AI scene images | `--images gemini` / `gemini-fallback` | Often needs billing |
| Local text cards | `--images cards` (default) | Yes |
| Voice | `--tts local` / `edge` / `silent` | Yes |
| NotebookLM / Flow video | Manual | See RESOURCES.md |

## What the automation does

One command creates:

1. Story package (hook, scenes, caption, hashtags)
2. Vertical scene card images (1080×1920)
3. AI voiceover (Microsoft Edge TTS — free)
4. Assembled `reel.mp4` with Ken Burns zoom (ffmpeg)
5. `caption.txt` ready to paste

## What it does **not** do (and why)

| Step | Auto? | Why |
|---|---|---|
| ChatGPT/Gemini research quality | Optional | Needs API key; free website chat is not automatable cleanly |
| Google Flow / Dreamina video | No | No reliable free public API for bots |
| CapCut Pro effects | No | No free automation API |
| Instagram posting | No (default) | Needs Meta Graph API + Business account + app review. Scraping/bots violate Instagram ToS |
| Guaranteed virality | No | Impossible to automate |

## How to run

```bash
cd faceless-story-system
# Windows PowerShell:
.\.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Fully free / offline (no API keys)
python -m automation --niche "forgotten Indian history" --provider offline

# If Edge TTS SSL fails on Windows, use local voice:
python -m automation --niche "forgotten Indian history" --provider offline --tts local

# Or skip voice and add trending audio later in CapCut:
python -m automation --niche "forgotten Indian history" --provider offline --tts silent

# Hindi voice (Edge TTS when SSL works)
python -m automation --niche "भारतीय इतिहास" --language hi --provider offline

# Multi-provider auto (uses whichever API keys exist)
python -m automation --niche "true crime mysteries" --provider auto --tts local
```


## Windows: `SSLCertVerificationError` (Gemini API or Edge TTS)

Common on Windows (Python CA store / antivirus HTTPS scanning).

**Fix Gemini / Groq / OpenRouter API calls:**
```bat
pip install -U certifi httpx
python -m automation --niche "forgotten Indian history" --provider gemini --model gemini-3.1-pro-preview --images cards --duration 30 --tts local
```

If it still fails (corporate SSL inspection), add to `.env`:
```env
FACELESS_SSL_INSECURE=1
```
(Use only on trusted networks.)

**Fix Edge TTS voice:**
```bat
pip install -U certifi pyttsx3 edge-tts
python -m automation ... --tts local
```

Default `--tts auto` falls back to local Windows SAPI, then silent audio.

## Windows: `WinError 2` / ffmpeg not found

Video assembly needs ffmpeg. The app now auto-uses a bundled binary via `imageio-ffmpeg` if system ffmpeg is missing.

```bat
pip install -U imageio-ffmpeg
python -m automation --niche "forgotten Indian history" --mode offline --tts silent
```

Optional system install:
```bat
winget install Gyan.FFmpeg
```
Then close and reopen the terminal.

### Output

```
reels/YYYY-MM-DD-title/
  package.json
  brief.md
  caption.txt
  stills/01.png …
  export/voice.mp3
  export/reel.mp4
  manifest.json
```

Then:

1. Open `export/reel.mp4`
2. (Optional) replace stills with richer AI images using `visual_prompt` from `package.json`
3. (Optional) drop the MP4 into CapCut and add trending Instagram audio
4. Upload to Instagram Reels and paste `caption.txt`

## Upgrade path (later)

| Upgrade | Needs |
|---|---|
| Better scripts | `OPENAI_API_KEY` or Gemini API key |
| Real AI images | Bing/Gemini/Leonardo API or manual export into `stills/` |
| Real AI video clips | Paid API or manual Flow/Dreamina downloads into timeline |
| Auto-publish | Meta Graph API app + Page + Instagram Business login |

## Reality check

Automation gets you from **idea → draft MP4** in minutes.  
The growth loop (story taste, posting consistency, reply/engagement) still needs a human.
