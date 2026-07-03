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

## Quick Setup

1. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Configure environment** (create a `.env` file):
   ```
   TWILIO_ACCOUNT_SID=your_sid
   TWILIO_AUTH_TOKEN=your_token
   GROQ_API_KEY=your_groq_key
   BASE_URL=https://your-deployed-url.com
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
│   └── groq_api.py         # AI responses + safety prompts
├── utils/
│   ├── helpers.py          # Input sanitization
│   └── compliance.py       # STOP/HELP, opt-out, content filters
├── templates/
│   ├── privacy.html
│   └── terms.html
└── requirements.txt
```

Built with Flask, Groq, and Twilio.
