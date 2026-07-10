# Keddy-bot TODO (accuracy improvements)

- [ ] 1) Add server-side web conversation history to `/chat` (session_id + store recent turns)
- [ ] 2) Update widget to persist a `session_id` in `localStorage` and send it with requests
- [ ] 3) Strengthen system prompt instructions for accuracy (clarifying questions, avoid guessing)
- [ ] 4) Improve memory formatting for consistency
- [ ] 5) Tune Groq generation parameters for lower variance (temperature/top_p) and add a one-shot retry self-check
- [ ] 6) Run `python -m py_compile` sanity check
- [ ] 7) Manual test widget continuity + ambiguous prompts behavior

