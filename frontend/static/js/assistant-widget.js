/**
 * Asisten SehatWarga - Floating Chat Widget
 * Safe DOM rendering, persistent session state, responsive panel.
 */
document.addEventListener('DOMContentLoaded', () => {
  const widget = document.getElementById('sw-chat-widget');
  if (!widget || window.__sehatWargaWidgetInitialized) return;
  window.__sehatWargaWidgetInitialized = true;

  const launcher = document.getElementById('sw-widget-launcher');
  const panel = document.getElementById('sw-widget-panel');
  const minimizeBtn = document.getElementById('sw-widget-minimize');
  const closeBtn = document.getElementById('sw-widget-close');
  const form = document.getElementById('sw-widget-form');
  const input = document.getElementById('sw-widget-input');
  const submitBtn = document.getElementById('sw-widget-submit');
  const messagesContainer = document.getElementById('sw-widget-messages');
  const chips = document.querySelectorAll('.sw-widget-chip');

  if (!launcher || !panel || !form || !input || !messagesContainer) return;

  const SESSION_STORAGE_KEY = 'sw_widget_chat_session_v1';
  let isBusy = false;
  const conversationHistory = [];
  const chatEntries = [];

  function getCsrfToken() {
    const inputToken = document.getElementById('sw-widget-csrf');
    if (inputToken && inputToken.value) return inputToken.value;
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken && metaToken.content) return metaToken.content;
    const fallbackInput = document.querySelector('input[name="csrf_token"]');
    if (fallbackInput && fallbackInput.value) return fallbackInput.value;
    return '';
  }

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function appendItalic(parent, text) {
    const pattern = /\*([^*\n]+)\*/g;
    let cursor = 0;
    for (const match of text.matchAll(pattern)) {
      parent.append(document.createTextNode(text.slice(cursor, match.index)));
      parent.append(el('em', '', match[1]));
      cursor = match.index + match[0].length;
    }
    parent.append(document.createTextNode(text.slice(cursor)));
  }

  function appendInlineMarkdown(parent, text) {
    const pattern = /\*\*([^\n]+?)\*\*/g;
    let cursor = 0;
    for (const match of text.matchAll(pattern)) {
      appendItalic(parent, text.slice(cursor, match.index));
      const strong = el('strong');
      appendItalic(strong, match[1]);
      parent.append(strong);
      cursor = match.index + match[0].length;
    }
    appendItalic(parent, text.slice(cursor));
  }

  function renderMessageText(text, markdown = false) {
    const container = el('div', 'message-text');
    const source = String(text ?? '');
    if (!markdown) {
      container.textContent = source;
      return container;
    }
    let list = null;
    let listType = null;
    let lastItem = null;

    source.split('\n').forEach(rawLine => {
      const line = rawLine.trim();
      const ordered = line.match(/^\d+[.)]\s+(.+)$/);
      const unordered = line.match(/^[-•]\s+(.+)$/);
      const match = ordered || unordered;

      if (match) {
        const type = ordered ? 'ol' : 'ul';
        if (!list || listType !== type) {
          list = el(type, 'message-list');
          container.append(list);
          listType = type;
        }
        lastItem = el('li');
        appendInlineMarkdown(lastItem, match[1]);
        list.append(lastItem);
        return;
      }

      if (/^\s+/.test(rawLine) && lastItem && line) {
        lastItem.append(document.createElement('br'));
        appendInlineMarkdown(lastItem, line);
        return;
      }

      list = null;
      listType = null;
      lastItem = null;

      if (!line) return;

      const paragraph = el('p');
      appendInlineMarkdown(paragraph, line);
      container.append(paragraph);
    });

    return container;
  }

  function scrollToBottom(force = false) {
    const threshold = 120;
    const isNearBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight < threshold;
    if (force || isNearBottom) {
      messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: 'smooth'
      });
    }
  }

  function saveSessionState() {
    try {
      const payload = {
        history: conversationHistory,
        entries: chatEntries,
        draft: input ? input.value : ''
      };
      sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload));
    } catch {
      // Storage unavailable or quota exceeded
    }
  }

  function restoreSessionState() {
    try {
      const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data) return;

      if (typeof data.draft === 'string' && data.draft && !input.value) {
        input.value = data.draft;
        resizeInput();
      }

      if (Array.isArray(data.entries) && data.entries.length > 0) {
        messagesContainer.innerHTML = '';
        conversationHistory.length = 0;
        chatEntries.length = 0;

        if (Array.isArray(data.history)) {
          data.history.forEach(item => conversationHistory.push(item));
        }

        // Always keep or prepend initial welcome message
        const first = data.entries[0];
        if (!first || !first.isWelcome) {
          const welcomeRow = el('div', 'message-row assistant-row');
          welcomeRow.append(el('div', 'message-avatar', 'SW'));
          const welcomeBubble = el('div', 'message-bubble');
          welcomeBubble.append(renderMessageText('Halo! Saya Asisten SehatWarga. Ada yang bisa saya bantu terkait layanan atau fasilitas kesehatan?', false));
          welcomeRow.append(welcomeBubble);
          messagesContainer.append(welcomeRow);
        }

        data.entries.forEach(entry => {
          chatEntries.push(entry);
          if (entry.isWelcome) {
            const row = el('div', 'message-row assistant-row');
            row.append(el('div', 'message-avatar', 'SW'));
            const bubble = el('div', 'message-bubble');
            bubble.append(renderMessageText(entry.text, false));
            row.append(bubble);
            messagesContainer.append(row);
          } else if (entry.isUser) {
            addRow(entry.text, true, false);
          } else if (entry.responseData) {
            renderResponse(entry.responseData, false);
          } else if (entry.text) {
            const bubble = addRow(entry.text, false, false);
            if (entry.isError) {
              bubble.classList.add('message-error');
              bubble.setAttribute('role', 'alert');
            }
          }
        });
        scrollToBottom(true);
      }
    } catch {
      // Ignore parse failure
    }
  }

  function addRow(text, isUser = false, record = true) {
    const row = el('div', `message-row ${isUser ? 'user-row' : 'assistant-row'}`);
    row.append(el('div', 'message-avatar', isUser ? 'Anda' : 'SW'));
    const bubble = el('div', 'message-bubble');
    bubble.append(renderMessageText(text, !isUser));
    row.append(bubble);
    messagesContainer.append(row);

    // Limit DOM message count
    while (messagesContainer.children.length > 40) {
      messagesContainer.firstElementChild.remove();
    }
    scrollToBottom(true);

    if (record && text) {
      chatEntries.push({ isUser, text });
      saveSessionState();
    }

    return bubble;
  }

  function setBusy(value) {
    isBusy = value;
    submitBtn.disabled = value;
    form.setAttribute('aria-busy', String(value));
    chips.forEach(b => { b.disabled = value; });
    document.querySelectorAll('.btn-location-action').forEach(b => { b.disabled = value; });
  }

  function resizeInput() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 84)}px`;
    input.style.overflowY = input.scrollHeight > 84 ? 'auto' : 'hidden';
  }

  function openPanel() {
    panel.hidden = false;
    panel.classList.add('is-open');
    launcher.hidden = true;
    launcher.classList.add('is-hidden');
    launcher.setAttribute('aria-expanded', 'true');
    panel.setAttribute('aria-hidden', 'false');

    requestAnimationFrame(() => {
      input.focus();
      scrollToBottom(true);
    });
  }

  function minimizePanel() {
    panel.hidden = true;
    panel.classList.remove('is-open');
    launcher.hidden = false;
    launcher.classList.remove('is-hidden');
    launcher.setAttribute('aria-expanded', 'false');
    panel.setAttribute('aria-hidden', 'true');
    saveSessionState();
    launcher.focus();
  }

  function closePanel() {
    minimizePanel();
  }

  function createFacilityCard(f) {
    const card = el('article', 'facility-result-item');
    card.append(
      el('h3', 'facility-result-name', f.name),
      el('p', 'facility-result-meta', `${f.facility_type_label || f.facility_type} · ${f.city || ''}`),
      el('p', 'facility-result-meta', f.address || 'Alamat belum tersedia')
    );
    if (typeof f.distance_km === 'number') {
      card.append(el('p', 'facility-result-distance', `± ${f.distance_km} km (perkiraan garis lurus)`));
    }
    if (Number.isInteger(f.id) && f.id > 0) {
      const link = el('a', 'facility-result-link', 'Lihat Detail Fasilitas →');
      link.href = `/facilities/${f.id}`;
      card.append(link);
    }
    if (typeof f.action_url === 'string' && f.action_url.startsWith('/')) {
      const action = el('a', 'facility-result-action', 'Ajukan layanan ini');
      action.href = f.action_url;
      card.append(action);
    }
    return card;
  }

  function renderResponse(data, record = true) {
    const bubble = addRow(data.message || 'Tidak ada informasi yang tersedia.', false, false);

    // Service recommendation card
    if (data.service_recommendation && typeof data.service_recommendation === 'object') {
      const rec = el('section', 'service-recommendation-card');
      rec.setAttribute('aria-label', 'Rekomendasi layanan SehatWarga AI');
      rec.append(
        el('span', 'service-recommendation-kicker', 'AI HEALTH NAVIGATOR'),
        el('h3', 'service-recommendation-title', data.service_recommendation.label || 'Rekomendasi layanan'),
        el('p', 'service-recommendation-basis', data.service_recommendation.basis || 'Data terverifikasi'),
        el('p', 'service-recommendation-disclaimer', data.service_recommendation.disclaimer || 'Bukan diagnosis medis.')
      );
      bubble.append(rec);
    }

    // Geolocation prompt
    if (data.requires_location) {
      const locCard = el('div', 'location-request-card');
      locCard.append(el('p', 'location-request-text', 'Bagikan lokasi untuk mencari fasilitas terdekat di sekitar Anda.'));
      const locBtn = el('button', 'btn-location-action', 'Gunakan Lokasi Saya');
      locBtn.type = 'button';
      locBtn.addEventListener('click', () => {
        if (isBusy) return;
        if (!navigator.geolocation) {
          addRow('Geolokasi tidak tersedia pada peramban ini. Sebutkan nama kota melalui pesan.');
          return;
        }
        setBusy(true);
        locBtn.textContent = 'Meminta lokasi…';
        navigator.geolocation.getCurrentPosition(
          pos => {
            setBusy(false);
            locBtn.textContent = 'Gunakan Lokasi Saya';
            const payload = {
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude,
              facility_type: data.facility_type || null
            };
            sendLocationRequest(form.dataset.locationUrl, payload, () => locBtn.click());
          },
          () => {
            setBusy(false);
            locBtn.textContent = 'Gunakan Lokasi Saya';
            addRow('Lokasi tidak dapat diakses. Anda tetap dapat mencari fasilitas berdasarkan kota.');
          },
          { timeout: 10000, enableHighAccuracy: false, maximumAge: 0 }
        );
      });
      locCard.append(locBtn);
      bubble.append(locCard);
    }

    // Facility list
    if (Array.isArray(data.facilities) && data.facilities.length > 0) {
      const list = el('div', 'facility-results-list');
      data.facilities.slice(0, 5).forEach(f => list.append(createFacilityCard(f)));
      bubble.append(list);
    }

    if (record) {
      chatEntries.push({ isUser: false, responseData: data });
      saveSessionState();
    }

    scrollToBottom(true);
  }

  async function sendLocationRequest(url, payload, retryFn) {
    if (isBusy) return;
    setBusy(true);
    const typing = addRow('Sedang mencari fasilitas terdekat…', false, false);
    typing.classList.add('typing-indicator');
    typing.prepend(el('span', 'spinner'));

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      let data;
      try {
        data = await res.json();
      } catch {
        throw new Error('Respons server tidak tersedia.');
      }

      if (!res.ok || !data.success) {
        throw new Error(data.message || 'Permintaan lokasi gagal.');
      }

      renderResponse(data);
    } catch (error) {
      const errBubble = addRow(error.name === 'AbortError' ? 'Waktu permintaan habis. Silakan coba kembali.' : error.message, false, false);
      errBubble.classList.add('message-error');
      errBubble.setAttribute('role', 'alert');

      chatEntries.push({ isUser: false, text: error.name === 'AbortError' ? 'Waktu permintaan habis. Silakan coba kembali.' : error.message, isError: true });
      saveSessionState();

      const retryBtn = el('button', 'btn btn-outline-primary', 'Coba lagi');
      retryBtn.type = 'button';
      retryBtn.style.marginTop = '8px';
      retryBtn.addEventListener('click', () => {
        if (!isBusy) {
          errBubble.parentElement.remove();
          retryFn();
        }
      });
      errBubble.append(retryBtn);
    } finally {
      clearTimeout(timeout);
      typing.parentElement.remove();
      setBusy(false);
    }
  }

  async function sendChatRequest(url, payload, retryFn) {
    if (isBusy) return;
    setBusy(true);

    const typing = addRow('Sedang menyiapkan jawaban…', false, false);
    typing.classList.add('typing-indicator');
    typing.prepend(el('span', 'spinner'));

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      let data;
      try {
        data = await res.json();
      } catch {
        throw new Error('Respons server tidak tersedia. Muat ulang halaman jika sesi telah berakhir.');
      }

      if (!res.ok || !data.success) {
        throw new Error(data.message || 'Permintaan gagal. Silakan coba kembali.');
      }

      if (data.message) {
        conversationHistory.push({ role: 'assistant', content: String(data.message).slice(0, 2000) });
        if (conversationHistory.length > 10) conversationHistory.shift();
      }

      renderResponse(data);
    } catch (error) {
      const errBubble = addRow(error.name === 'AbortError' ? 'Waktu permintaan habis. Silakan coba kembali.' : error.message, false, false);
      errBubble.classList.add('message-error');
      errBubble.setAttribute('role', 'alert');

      chatEntries.push({ isUser: false, text: error.name === 'AbortError' ? 'Waktu permintaan habis. Silakan coba kembali.' : error.message, isError: true });
      saveSessionState();

      const retryBtn = el('button', 'btn btn-outline-primary', 'Coba lagi');
      retryBtn.type = 'button';
      retryBtn.style.marginTop = '8px';
      retryBtn.addEventListener('click', () => {
        if (!isBusy) {
          errBubble.parentElement.remove();
          retryFn();
        }
      });
      errBubble.append(retryBtn);
    } finally {
      clearTimeout(timeout);
      typing.parentElement.remove();
      setBusy(false);
    }
  }

  function sendMessage(text) {
    if (isBusy || !text || !text.trim()) return;
    const cleanText = text.trim().slice(0, 2000);

    addRow(cleanText, true);
    input.value = '';
    resizeInput();
    saveSessionState();

    // Track user message in history
    conversationHistory.push({ role: 'user', content: cleanText });
    if (conversationHistory.length > 10) conversationHistory.shift();

    const payload = {
      message: cleanText,
      conversation_history: conversationHistory.slice(-6)
    };

    const chatUrl = form.dataset.chatUrl || '/assistant/chat';
    sendChatRequest(chatUrl, payload, () => sendChatRequest(chatUrl, payload, () => sendMessage(cleanText)));
  }

  // Restore saved session on load if available
  restoreSessionState();

  // Event Listeners
  launcher.addEventListener('click', openPanel);
  minimizeBtn.addEventListener('click', minimizePanel);
  closeBtn.addEventListener('click', closePanel);

  form.addEventListener('submit', e => {
    e.preventDefault();
    sendMessage(input.value);
  });

  input.addEventListener('input', () => {
    resizeInput();
    saveSessionState();
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !panel.hidden && panel.contains(document.activeElement)) {
      minimizePanel();
    }
  });

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      if (chip.dataset.query) {
        sendMessage(chip.dataset.query);
      }
    });
  });

  resizeInput();
});
