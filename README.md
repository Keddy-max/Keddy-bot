# Keddy WhatsApp AI Assistant

A professional WhatsApp AI assistant powered by Groq (Llama 3.1), built for Meta/WhatsApp Business Platform compliance via Twilio.

**Creator:** Prince Ked Agbemenu

## Features

- AI-powered conversational replies (formal English or Nigerian Pidgin)
- **Voice notes** — transcribed via Groq Whisper and answered as text
- **Images** — analyzed via Groq vision (describe, OCR, answer questions)
- Twilio WhatsApp webhook with signature validation
- Privacy Policy and Terms of Service pages (required for Meta approval)
- STOP / START / HELP / DELETE / PRIVACY compliance commands
- Content safety filters and professional AI guardrails
- Privacy-conscious logging (hashed user identifiers)
- Rate limiting to prevent abuse

## Image Understanding (Vision)

Keddy can receive images from WhatsApp and send them to a vision-capable AI model for understanding. It supports:

- Images with captions or questions
- Images without captions (brief description + offer to help)
- OCR / text extraction from images
- Screenshot analysis
- Document/photo interpretation
- Charts and diagram explanation
- Multiple images in one message
- Follow-up questions about a previously analyzed image

### How the image flow works

```
WhatsApp user
   ↓ sends image (+ optional caption)
Twilio webhook (/whatsapp)
   ↓ parse_incoming_message(): downloads the actual image bytes
services/media.py (MIME/size validation, multi-image support)
   ↓
services/vision.py  analyze_image()  (reusable vision service)
   ├─ Groq vision model (default)  OR  a generic VISION_API_URL provider
   ├─ sends BOTH the image bytes and the user's text
   └─ includes conversation history for follow-up context
   ↓
services/groq_api.py  get_keddy_image_reply()  (backward-compatible wrapper)
routes/whatsapp.py
   ↓
AI response sent back to WhatsApp via TwiML
```

The actual image (not just a filename/URL) is sent to the model. Media is
processed in memory — images are never stored permanently.

### Vision configuration (env vars)

| Variable | Description | Default |
|----------|-------------|---------|
| `VISION_MODEL` | Vision model name | `llama-3.2-11b-vision-preview` |
| `VISION_API_KEY` | Optional override; falls back to `GROQ_API_KEY` | _unset_ |
| `VISION_API_URL` | Optional generic OpenAI-style vision endpoint | _unset_ |
| `VISION_TIMEOUT_SECONDS` | Request timeout | `60` |
| `VISION_MAX_TOKENS` | Max response tokens | `600` |
| `VISION_TEMPERATURE` | Sampling temperature | `0.22` |

### Supported image formats

`JPEG/JPG`, `PNG`, `WEBP` (plus `GIF`/`AVIF` if your provider supports them).
Unsupported formats return a clear friendly message.

### Vision model limitations

- The default Groq vision model (`llama-3.2-11b-vision-preview`) is a preview
  model; accuracy on dense text, small details, or complex charts may vary.
- Images are limited to ~6MB (Twilio/Twilio media limit).
- Follow-up questions work best within the same conversation session; the
  stored "last image context" is short (~300 chars) and cleared on `DELETE`/`STOP`.

## Quick Setup

1. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Configure environment** (copy `.env.example` to `.env` and fill in your values):
   ```
   TWILIO_ACCOUNT_SID=your_sid
   TWILIO_AUTH_TOKEN=your_token
   GROQ_API_KEY=your_groq_key
   BASE_URL=https://your-deployed-url.com

   # Optional vision overrides (Groq vision is used by default)
   VISION_MODEL=llama-3.2-11b-vision-preview
   VISION_API_KEY=
   VISION_API_URL=
   ```

3. **Configure Twilio WhatsApp:**
   - Go to [Twilio Console](https://console.twilio.com/)
   - Set webhook URL to `https://your-url.com/whatsapp` (POST)

4. **Run locally:**
   ```
   python app.py
   ```
   Use ngrok for local testing: `ngrok http 5000`

## Compliance Endpoints

| URL | Purpose |
|-----|---------|
| `/privacy` | Privacy Policy (submit this URL to Meta) |
| `/terms` | Terms of Service |
| `/whatsapp` | Twilio webhook (POST) |
| `/status` | Health check |

## WhatsApp Commands

Users can send these keywords at any time:

| Command | Action |
|---------|--------|
| `HELP` | Show usage and policy links |
| `STOP` | Opt out of messages |
| `START` | Re-subscribe |
| `DELETE` | Clear conversation history |
| `PRIVACY` | Get privacy policy link |

## Deploy to Render (24/7)

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo
3. Settings:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
4. **Environment Variables:**
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `GROQ_API_KEY`
   - `BASE_URL` — your Render URL (e.g. `https://keddy-bot.onrender.com`)
5. Update Twilio webhook to `https://your-render-url.onrender.com/whatsapp`

## Meta / WhatsApp Business Approval Checklist

Before submitting for Meta approval (via Twilio or Meta Business Manager):

### Required (code is ready)
- [x] Privacy Policy URL (`/privacy`)
- [x] Terms of Service URL (`/terms`)
- [x] STOP / opt-out handling
- [x] First-message consent disclosure
- [x] AI disclaimer (no medical/legal/financial advice)
- [x] Webhook signature validation
- [x] Content safety filters
- [x] Data deletion command (DELETE)

### Required (you configure in dashboards)
- [ ] **Meta Business Verification** — verify your business in Meta Business Manager
- [ ] **WhatsApp Business Profile** — display name, description, category, profile photo
- [ ] **Production phone number** — move from Twilio Sandbox to approved business number
- [ ] **Privacy Policy URL in Meta App** — paste `https://your-url.com/privacy`
- [ ] **BASE_URL env var** — set to your production URL on Render
- [ ] **Business display name** — must match your verified business (e.g. "Keddy Assistant")

### Recommended
- [ ] UptimeRobot ping to `/status` every 5 min (keeps Render free tier awake)
- [ ] Custom domain for professional URLs
- [ ] Message templates for outbound messages outside 24-hour window

## Project Structure

```
Keddy-bot/
├── app.py                  # Flask entry point
├── routes/
│   ├── whatsapp.py         # Twilio webhook + compliance
│   └── legal.py            # Privacy & terms pages
├── services/
│   ├── groq_api.py         # AI responses + safety prompts
│   ├── vision.py           # Reusable vision service (image understanding)
│   └── media.py            # Twilio media download + validation
├── utils/
│   ├── helpers.py          # Input sanitization
│   └── compliance.py       # STOP/HELP, opt-out, content filters
├── templates/
│   ├── privacy.html
│   └── terms.html
└── requirements.txt
```

Built with Flask, Groq, and Twilio.
