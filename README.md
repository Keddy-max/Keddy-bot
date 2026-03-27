# Keddy WhatsApp AI Chatbot 🐳

A friendly WhatsApp bot powered by Groq's Llama3 AI. Replies to messages with helpful, playful responses.

## 🚀 Quick Setup

1. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

2. **Configure Twilio** (for WhatsApp sandbox):
   - Go to [Twilio Console](https://console.twilio.com/)
   - Create Messaging Service or use Sandbox (# join code provided)
   - Set webhook URL to `https://your-ngrok.ngrok.io/whatsapp` (POST)

3. **Expose local server**:
   ```
   ngrok http 5000
   ```
   Copy the ngrok URL.

4. **Run the bot**:
   ```
   python app.py
   ```

5. **Test**:
   - Send WhatsApp msg to sandbox number/join code.
   - Bot replies via Groq AI!

## 🔧 Environment Variables (.env)
```
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
GROQ_API_KEY=your_groq_key
```

## 📱 Features
- AI-powered replies (Keddy personality)
- Twilio WhatsApp webhook
- Local dev with ngrok
- Logging & error handling

## ☁️ Deploy to Render (24/7)

1. Go [render.com](https://render.com), Dashboard → New → Web Service.
2. Connect GitHub repo: Keddy-max/Keddy-bot.
3. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Plan: Free
4. Environment Vars: Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, GROQ_API_KEY from .env.
5. Deploy → URL ready!

Update Twilio webhook to Render URL/whatsapp.

## 🛠️ Development
- Edit `services/groq_api.py` for model/personality
- `python app.py` (debug=True)

Built with ❤️ using Flask + Groq + Twilio.

