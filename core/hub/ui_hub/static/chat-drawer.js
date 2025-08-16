(function () {
  const state = { open: false, loading: false, messages: [] };
  const LS_KEY = 'hub_chat_history';

  function save() { try { localStorage.setItem(LS_KEY, JSON.stringify(state.messages)); } catch {} }
  function load() { try { state.messages = JSON.parse(localStorage.getItem(LS_KEY) || '[]'); } catch { state.messages = []; } }

  function el(tag, attrs = {}, children = []) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') e.className = v;
      else if (k === 'text') e.textContent = v;
      else e.setAttribute(k, v);
    });
    const kids = Array.isArray(children) ? children : [children];
    kids.filter(c => c !== undefined && c !== null).forEach(c => {
      if (typeof c === 'string' || typeof c === 'number') {
        e.appendChild(document.createTextNode(String(c)));
      } else if (c && typeof c === 'object' && 'nodeType' in c) {
        e.appendChild(c);
      }
    });
    return e;
  }

  function render() {
    const msgs = document.getElementById('hub-chat-messages');
    if (!msgs) return;
    msgs.innerHTML = '';
    if (!state.messages.length) {
      msgs.appendChild(el('div', { id: 'hub-chat-empty', text: '👋 Hi! Ask the hub assistant anything.' }));
    } else {
      state.messages.forEach(m => {
        msgs.appendChild(el('div', { class: `hub-msg ${m.type}` }, [
          el('div', { text: m.content }),
          el('div', { style: 'font-size:10px; opacity:.7; margin-top:4px;', text: m.time })
        ]));
      });
      msgs.scrollTop = msgs.scrollHeight;
    }
    const loading = document.getElementById('hub-chat-loading');
    if (loading) loading.style.display = state.loading ? 'block' : 'none';
  }

  function now() { try { return new Date().toLocaleTimeString(); } catch { return ''; } }

  async function send() {
    if (state.loading) return;
    const ta = document.getElementById('hub-chat-textarea');
    if (!ta) return;
    const text = (ta.value || '').trim();
    if (!text) return;
    const msg = { id: Date.now(), type: 'user', content: text, time: now() };
    state.messages.push(msg); save();
    ta.value = '';
    state.loading = true; render();
    try {
      // Build OpenAI-style message array using local history
      const history = [];
      for (const m of state.messages) {
        if (m.type === 'user') history.push({ role: 'user', content: m.content });
        if (m.type === 'ai') history.push({ role: 'assistant', content: m.content });
      }
      history.push({ role: 'user', content: text });

      const r = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history })
      });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const data = await r.json();
      state.messages.push({ id: Date.now() + 1, type: 'ai', content: (data.response || '...'), time: now() });
      save();
    } catch (e) {
      state.messages.push({ id: Date.now() + 1, type: 'ai', content: 'Sorry, there was an error. Please try again.', time: now() });
      save();
      console.error('[hub-chat] send error:', e);
    } finally {
      state.loading = false; render();
    }
  }

  async function clearSession() {
    try { await fetch('/api/agent/session', { method: 'DELETE' }); } catch {}
    state.messages = []; save(); render();
  }

  function mount() {
    if (document.getElementById('hub-chat-drawer')) return;
    const toggle = el('button', { id: 'hub-chat-toggle', title: 'Open Chat' }, '💬');
    const drawer = el('div', { id: 'hub-chat-drawer' }, [
      el('div', { id: 'hub-chat-header' }, [
        el('h3', { style: 'margin:0;font-size:16px;', text: '🤖 Hub Chat' }),
        el('button', { id: 'hub-chat-clear', title: 'Clear' }, 'Clear')
      ]),
      el('div', { id: 'hub-chat-messages' }),
      el('div', { id: 'hub-chat-loading', text: 'Thinking...' }),
      el('div', { id: 'hub-chat-input' }, [
        el('textarea', { id: 'hub-chat-textarea', rows: '3', placeholder: 'Ask the hub assistant...' }),
        el('button', { id: 'hub-chat-send' }, 'Send')
      ])
    ]);
    document.body.appendChild(toggle);
    document.body.appendChild(drawer);

    function setOpen(v) {
      state.open = v;
      drawer.classList.toggle('open', !!v);
      toggle.textContent = v ? '✕' : '💬';
      toggle.title = v ? 'Close Chat' : 'Open Chat';
    }
    toggle.addEventListener('click', () => setOpen(!state.open));
    document.getElementById('hub-chat-send').addEventListener('click', send);
    document.getElementById('hub-chat-textarea').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    document.getElementById('hub-chat-clear').addEventListener('click', clearSession);

    load(); render();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();



