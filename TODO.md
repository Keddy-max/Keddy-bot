# Keddy-bot TODO (image understanding / vision upgrade)

## Vision support enhancement
- [x] 1) Create reusable `services/vision.py` with configurable `analyze_image()`
- [x] 2) Harden `services/media.py`: multi-image download + MIME/size validation
- [x] 3) Improve `routes/whatsapp.py`: image routing, follow-up context, friendly errors
- [x] 4) Refactor `services/groq_api.py` to delegate to vision service (keep backward compat)
- [x] 5) Add `.env.example` with vision config docs
- [x] 6) Update README with vision feature, env vars, limitations
- [x] 7) Run `python -m py_compile` sanity check on all changed files
- [ ] 8) Manual test through WhatsApp (requires live Twilio + Groq keys)
