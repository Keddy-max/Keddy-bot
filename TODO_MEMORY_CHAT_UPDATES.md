# TODO: Natural Conversation Upgrade (Keddy)

- [ ] Create modular Groq system prompt module/file
- [ ] Update Groq generation parameters (temperature/top_p/max_tokens + penalties if supported)
- [ ] Improve conversation memory: summarize + include recent turns; preserve existing WhatsApp history
- [ ] Improve response post-processing (trim repeats, avoid overly long responses)
- [ ] Update WhatsApp UX strings (welcome/empty/error) to be less robotic
- [ ] Update web widget UX (varied greeting, nicer error copy)
- [ ] Refactor duplicated history trimming logic if needed
- [ ] Add/adjust comments and keep architecture intact
- [ ] Run quick import/lint sanity check (python -m py_compile)

