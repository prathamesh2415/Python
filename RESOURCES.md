# Free & low-cost resources for this product

Practical stack for faceless story Reels (Nov 2026). Limits change — re-check provider dashboards.

## 1. Script / research APIs (wired into this CLI)

| Provider | Env key | Suggested models | Free reality |
|---|---|---|---|
| **Google Gemini** | `GEMINI_API_KEY` | `gemini-3.1-flash-lite` (fast), `gemini-3.1-pro-preview` (quality; if your project allows) | Free tier via AI Studio; limits shown in AI Studio |
| **Groq** | `GROQ_API_KEY` | `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` | ~30 RPM / ~1k req/day per free model |
| **OpenRouter `:free`** | `OPENROUTER_API_KEY` | any model id ending in `:free` | ~20 RPM / ~50 req/day (higher after buying ≥10 credits once) |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o-mini` | Paid (optional backup) |
| **Offline** | none | built-in templates | Unlimited |

### Get keys

1. Gemini: https://aistudio.google.com/apikey  
2. Groq: https://console.groq.com/keys  
3. OpenRouter: https://openrouter.ai/keys  

**Gemini app Pro / Advanced ≠ API access.** You still need an AI Studio API key. Then set Pro/Flash explicitly:

```env
GEMINI_API_KEY=...
GEMINI_TEXT_MODEL=gemini-3.1-pro-preview
```

```bat
python -m automation --niche "forgotten Indian history" --provider gemini --model gemini-3.1-pro-preview --tts local
```

Auto failover (uses whichever keys exist):

```bat
python -m automation --niche "forgotten Indian history" --provider auto --tts local
```

Order: Gemini → Groq → OpenRouter → OpenAI → offline templates.

---

## 2. Images

| Tool | Cost | How to use with this project |
|---|---|---|
| Local text cards | Free | Default `--images cards` |
| Gemini image models | Often needs billing | `--images gemini` or `gemini-fallback` |
| Bing Image Creator | Free (manual) | Generate PNGs → drop into `stills/` → `python -m automation stitch --stills ...` |
| Gemini app image | Free/limits (manual) | Same stitch path |
| Leonardo free credits | Free daily (manual) | Same stitch path |

---

## 3. Video helpers (manual — no public bot API)

### NotebookLM / Gemini Notebook — Video Overview

Good for research-based explainer/short videos from sources.

1. Open Gemini Notebook / NotebookLM  
2. Create a notebook and add sources (articles, notes, PDFs)  
3. Studio panel → **Video Overview**  
4. Pick format: **Short (~60s)** for Reels-like length, or Explainer/Cinematic  
5. Generate → **Download**  
6. Optional: trim/add trending audio in CapCut, then post  

This is a **parallel path**, not automated by `python -m automation`.

### Google Flow

- ~50 free credits/day (doesn’t roll over)  
- Avoid peak hours (~14:00–17:00 UTC) when free video may be blocked  
- Use for a few cinematic clips; stitch with CapCut or replace individual stills  

### Dreamina

- Free daily credits for Seedance-style video  
- Good Flow backup when credits are empty  

### CapCut / Instagram Edits

- Final assembly, captions, trending audio  
- Avoid CapCut Pro-locked assets (watermark trap)  

---

## 4. Voice (already in CLI)

| Engine | Flag | Notes |
|---|---|---|
| Edge TTS | `--tts edge` / `auto` | Free online; Windows SSL issues common |
| Windows SAPI / pyttsx3 | `--tts local` | Offline; recommended on Windows |
| Silent bed | `--tts silent` | Add music later in CapCut |

---

## 5. Recommended product loop (A + C, 30-second hooks)

**A** = `--images cards` (free)  
**C** = `--provider auto` (Gemini → Groq → OpenRouter → offline)

```bat
python -m automation --niche "forgotten Indian history" --provider auto --images cards --duration 30 --tts local
```

For maximum script quality with your Pro access:

```bat
pip install -U certifi httpx
python -m automation --niche "forgotten Indian history" --provider gemini --model gemini-3.1-pro-preview --images cards --duration 30 --tts local
```

If Windows shows `CERTIFICATE_VERIFY_FAILED`, add `FACELESS_SSL_INSECURE=1` to `.env` (last resort for antivirus SSL inspection).

Loop:
1. Research notes in NotebookLM (optional)  
2. Run the 30s command above (hook-first JSON script)  
3. Open `export/reel.mp4` → CapCut + trending audio → Instagram  
4. Optional longer content: NotebookLM Video Overview download  

---

## 6. What we will not automate

- NotebookLM Video Overview generation (no stable public API)  
- Google Flow / Dreamina credit UIs  
- Instagram posting (needs Meta Graph API + Business setup)  
