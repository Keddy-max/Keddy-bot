# Deploy updates to Render (Flask)

The app is already deployed as a Render Web Service using `gunicorn app:app`.
This update adds:
- `POST /chat` (text-only web chat)
- `static/widget.js` + `static/widget.css` for embeddable widget

## 1) Environment variables

Ensure these are set in Render:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `GROQ_API_KEY`
- `BASE_URL` (example: `https://keddy-bot.onrender.com`)

No extra env vars are required for CORS.

## 2) Build / Start commands (unchanged)

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

## 3) Static files

Flask serves `/static/*` automatically from the `static/` directory.
So the widget embed must reference:

`https://YOUR-RENDER-APP.onrender.com/static/widget.js`

## 4) Verify

- `GET /status` should return healthy
- `POST /chat` should return JSON with `reply`

Example curl:

```bash
curl -X POST https://YOUR-RENDER-APP.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

## 5) WhatsApp remains unchanged

The Twilio webhook route `/whatsapp` and compliance handling stay in `routes/whatsapp.py`.
The only sharing change is that text-only reply generation uses the shared `get_bot_response()` wrapper.

