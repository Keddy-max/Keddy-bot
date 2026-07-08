(function () {
  const APP_ORIGIN = window.location.origin;

  // The API endpoint is always the same on the deployed Flask app.
  const CHAT_ENDPOINT = '/chat';

  const STYLE_ID = 'keddy-widget-style';

  function ensureCSS() {
    if (document.getElementById(STYLE_ID)) return;

    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    // Served automatically by Flask from /static
    link.href = `${APP_ORIGIN}/static/widget.css`;
    document.head.appendChild(link);
  }

  function safeText(str) {
    return String(str ?? '');
  }

  function createEl(tag, className) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    return el;
  }

  function scrollToBottom(container) {
    container.scrollTop = container.scrollHeight;
  }

  function setTyping(isTyping) {
    typingEl.style.display = isTyping ? 'flex' : 'none';
  }

  function addMessage(text, sender) {
    const bubble = createEl('div', `keddy-bubble keddy-${sender}`);
    bubble.textContent = safeText(text);
    messagesEl.appendChild(bubble);
    scrollToBottom(messagesEl);
  }

  function setError(text) {
    const bubble = createEl('div', 'keddy-bubble keddy-error');
    bubble.textContent = safeText(text);
    messagesEl.appendChild(bubble);
    scrollToBottom(messagesEl);
  }

  function openWidget() {
    widgetRoot.classList.add('open');
    toggleButton.setAttribute('aria-expanded', 'true');
    // Focus input after opening animation tick
    setTimeout(() => inputEl.focus(), 150);
  }

  function closeWidget() {
    widgetRoot.classList.remove('open');
    toggleButton.setAttribute('aria-expanded', 'false');
  }

  async function postChat(message) {
    const resp = await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`Server error (${resp.status}). ${text}`.trim());
    }

    const data = await resp.json();
    if (!data || typeof data.reply !== 'string') {
      throw new Error('Unexpected server response');
    }
    return data.reply;
  }

  function wireEvents() {
    toggleButton.addEventListener('click', () => {
      if (widgetRoot.classList.contains('open')) closeWidget();
      else openWidget();
    });

    closeButton.addEventListener('click', closeWidget);

    sendButton.addEventListener('click', async () => {
      const msg = inputEl.value.trim();
      if (!msg) return;

      addMessage(msg, 'user');
      inputEl.value = '';
      setTyping(true);

      try {
        const reply = await postChat(msg);
        addMessage(reply, 'bot');
      } catch (err) {
        setError('Sorry — the chat service is unavailable right now. Please try again later.');
        console.error('[Keddy widget] /chat error:', err);
      } finally {
        setTyping(false);
      }
    });

    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendButton.click();
      }
    });
  }

  ensureCSS();

  // Create widget DOM
  const widgetRoot = createEl('div', 'keddy-widget');
  widgetRoot.setAttribute('id', 'keddy-widget-root');

  const toggleButton = createEl('button', 'keddy-toggle');
  toggleButton.type = 'button';
  toggleButton.setAttribute('aria-label', 'Open chat');
  toggleButton.setAttribute('aria-expanded', 'false');
  toggleButton.textContent = '💬';

  const chatPanel = createEl('div', 'keddy-panel');

  const header = createEl('div', 'keddy-header');
  const title = createEl('div', 'keddy-title');
  title.textContent = 'Keddy Assistant';

  const closeButton = createEl('button', 'keddy-close');
  closeButton.type = 'button';
  closeButton.setAttribute('aria-label', 'Close chat');
  closeButton.textContent = '×';

  header.appendChild(title);
  header.appendChild(closeButton);

  const messagesEl = createEl('div', 'keddy-messages');

  const typingEl = createEl('div', 'keddy-typing');
  typingEl.innerHTML = '<span></span><span></span><span></span><div class="keddy-typing-text">Typing...</div>';

  const composer = createEl('div', 'keddy-composer');

  const inputWrap = createEl('div', 'keddy-input-wrap');
  const inputEl = createEl('input', 'keddy-input');
  inputEl.type = 'text';
  inputEl.placeholder = 'Type your message...';

  const sendButton = createEl('button', 'keddy-send');
  sendButton.type = 'button';
  sendButton.textContent = 'Send';

  inputWrap.appendChild(inputEl);
  inputWrap.appendChild(sendButton);

  composer.appendChild(inputWrap);

  chatPanel.appendChild(header);
  chatPanel.appendChild(messagesEl);
  chatPanel.appendChild(typingEl);
  chatPanel.appendChild(composer);

  widgetRoot.appendChild(toggleButton);
  widgetRoot.appendChild(chatPanel);

  document.body.appendChild(widgetRoot);

  // Expose refs used in helpers
  window.__keddyWidgetRefs = {
    widgetRoot,
    toggleButton,
    messagesEl,
    inputEl,
    sendButton,
    typingEl,
    closeButton,
  };

  // Initial system message
  addMessage('Hi! How can I help you today?', 'bot');
  setTyping(false);

  // Wire events after globals are set
  wireEvents();
})();

