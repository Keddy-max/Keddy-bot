# Keddy-bot TODO

## Plan: Add embeddable website chat widget + /chat API without breaking WhatsApp

- [x] Step 1: Refactor shared bot reply generation into reusable function `get_bot_response(message)` (and optional history/mode helpers) in a new module.
- [x] Step 2: Add Flask route `POST /chat` that accepts `{ "message": "..." }` and returns `{ "reply": "..." }`.
- [x] Step 3: Keep WhatsApp webhook logic in `routes/whatsapp.py` separate; update it to call the shared reply generation function.
- [x] Step 4: Add CORS support for the API endpoint (and widget assets if needed).
- [x] Step 5: Add static widget files `widget.js` and `widget.css` served from Flask.
- [x] Step 6: Ensure widget is embeddable via only `<script src="https://YOUR-RENDER-APP.onrender.com/static/widget.js"></script>`.
- [x] Step 7: Add deployment instructions for Render (env vars + static file serving).

- [ ] Step 8: Manual tests: verify WhatsApp webhook unchanged and `/chat` works from a browser.



