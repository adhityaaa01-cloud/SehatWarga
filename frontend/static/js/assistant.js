/** Read-only assistant: transient conversation, safe DOM, explicit location consent. */
document.addEventListener('DOMContentLoaded', () => {
  const messages=document.getElementById('chat-messages');
  const form=document.getElementById('chat-form');
  const input=document.getElementById('chat-input');
  const submit=document.getElementById('chat-submit');
  if(!form || window.__sehatWargaChatInitialized) return;
  window.__sehatWargaChatInitialized = true;
  const csrf=document.getElementById('csrf_token').value;
  let busy=false;
  const maps=[];
  function el(tag, cls, text) { const n=document.createElement(tag); if(cls) n.className=cls; if(text) n.textContent=text; return n; }

  function appendItalic(parent,text) {
    const pattern=/\*([^*\n]+)\*/g;
    let cursor=0;

    for(const match of text.matchAll(pattern)) {
      parent.append(document.createTextNode(text.slice(cursor,match.index)));
      parent.append(el('em','',match[1]));
      cursor=match.index+match[0].length;
    }

    parent.append(document.createTextNode(text.slice(cursor)));
  }

  function appendInlineMarkdown(parent,text) {
    const pattern=/\*\*([^\n]+?)\*\*/g;
    let cursor=0;

    for(const match of text.matchAll(pattern)) {
      appendItalic(parent,text.slice(cursor,match.index));
      const strong=el('strong');
      appendItalic(strong,match[1]);
      parent.append(strong);
      cursor=match.index+match[0].length;
    }

    appendItalic(parent,text.slice(cursor));
  }

  function renderMessageText(text,markdown=false) {
    const container=el('div','message-text');
    const source=String(text ?? '');

    if(!markdown) {
      container.textContent=source;
      return container;
    }

    let list=null;
    let listType=null;
    let lastItem=null;

    source.split('\n').forEach(rawLine => {
      const line=rawLine.trim();
      const ordered=line.match(/^\d+[.)]\s+(.+)$/);
      const unordered=line.match(/^[-•]\s+(.+)$/);
      const match=ordered || unordered;

      if(match) {
        const type=ordered ? 'ol' : 'ul';

        if(!list || listType!==type) {
          list=el(type,'message-list');
          container.append(list);
          listType=type;
        }

        lastItem=el('li');
        appendInlineMarkdown(lastItem,match[1]);
        list.append(lastItem);
        return;
      }

      if(/^\s+/.test(rawLine) && lastItem && line) {
        lastItem.append(document.createElement('br'));
        appendInlineMarkdown(lastItem,line);
        return;
      }

      list=null;
      listType=null;
      lastItem=null;

      if(!line) return;

      const paragraph=el('p');
      appendInlineMarkdown(paragraph,line);
      container.append(paragraph);
    });

    return container;
  }

  function row(text, user=false) {
    const r=el('div',`message-row ${user?'user-row':'assistant-row'}`);
    r.append(el('div','message-avatar',user?'Anda':'SW'));
    const bubble=el('div','message-bubble');
    bubble.append(renderMessageText(text,!user));
    r.append(bubble);
    messages.append(r);
    // Bound DOM and map resources; no durable chat storage.
    while(messages.children.length>40) {
      const first=messages.firstElementChild;
      maps.filter(m=>first.contains(m.getContainer())).forEach(m=>{m.remove();maps.splice(maps.indexOf(m),1);}); first.remove();
    }
    messages.scrollTop=messages.scrollHeight;
    return bubble;
  }
  function setBusy(value) {busy=value;submit.disabled=value;form.setAttribute('aria-busy',String(value));document.querySelectorAll('.suggested-pill,.btn-location-action').forEach(b=>b.disabled=value);}

  function resizeInput() {
    input.style.height='auto';
    input.style.height=`${Math.min(input.scrollHeight,96)}px`;
    input.style.overflowY=input.scrollHeight>96 ? 'auto' : 'hidden';
  }
  async function request(url,payload,retry) {
    if(busy) return;
    setBusy(true);
    const typing=row('Sedang menyiapkan jawaban…'); typing.classList.add('typing-indicator'); typing.prepend(el('span','spinner'));
    const controller=new AbortController(); const timeout=setTimeout(()=>controller.abort(),20000);
    try {
      const res=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(payload),signal:controller.signal});
      let data;
      try {data=await res.json();} catch {throw new Error('Respons server tidak tersedia. Muat ulang halaman jika sesi telah berakhir.');}
      if(!res.ok || !data.success) throw new Error(data.message || 'Permintaan gagal. Silakan coba kembali.');
      render(data);
    } catch(error) {
      const b=row(error.name==='AbortError'?'Waktu permintaan habis. Silakan coba kembali.':error.message);
      b.classList.add('message-error'); b.setAttribute('role','alert');
      const button=el('button','btn btn-outline-primary','Coba lagi');button.type='button';button.addEventListener('click',()=>{if(!busy){b.parentElement.remove();retry();}});b.append(button);
    } finally {clearTimeout(timeout);typing.parentElement.remove();setBusy(false);}
  }
  function send(message) {
    if(busy || !message.trim()) return;
    message=message.trim().slice(0,2000);
    row(message,true);
    input.value='';
    resizeInput();
    request(form.dataset.chatUrl,{message},()=>request(form.dataset.chatUrl,{message},()=>send(message)));
  }
  function hasCoords(f) {return typeof f.latitude==='number' && Number.isFinite(f.latitude) && Math.abs(f.latitude)<=90 && typeof f.longitude==='number' && Number.isFinite(f.longitude) && Math.abs(f.longitude)<=180;}
  function facilityCard(f) {
    const card=el('article','facility-result-item');
    card.append(el('h2','facility-result-name',f.name),el('p','facility-result-meta',`${f.facility_type_label || f.facility_type} · ${f.city || ''}`),el('p','facility-result-meta',f.address || 'Alamat belum tersedia'));
    if(typeof f.distance_km==='number') card.append(el('p','facility-result-distance',`± ${f.distance_km} km (perkiraan garis lurus)`));
    if(Number.isInteger(f.id) && f.id>0) {const link=el('a','facility-result-link','Lihat Detail Fasilitas →');link.href=`/facilities/${f.id}`;card.append(link);}
    if(typeof f.action_url==='string' && f.action_url.startsWith('/')) {
      const action=el('a','facility-result-action','Ajukan layanan ini');
      action.href=f.action_url;
      card.append(action);
    }
    return card;
  }
  function render(data) {
    const bubble=row(data.message || 'Tidak ada informasi yang tersedia.');
    if(data.service_recommendation && typeof data.service_recommendation==='object') {
      const recommendation=el('section','service-recommendation-card');
      recommendation.setAttribute(
        'aria-label',
        'Rekomendasi layanan SehatWarga AI'
      );
      recommendation.append(
        el('span','service-recommendation-kicker','AI HEALTH NAVIGATOR'),
        el(
          'h2',
          'service-recommendation-title',
          data.service_recommendation.label || 'Rekomendasi layanan'
        ),
        el(
          'p',
          'service-recommendation-basis',
          data.service_recommendation.basis || 'Data terverifikasi'
        ),
        el(
          'p',
          'service-recommendation-disclaimer',
          data.service_recommendation.disclaimer || 'Bukan diagnosis medis.'
        )
      );
      bubble.append(recommendation);
    }
    if(data.requires_location) {
      const card=el('div','location-request-card');card.append(el('p','location-request-text','Bagikan lokasi untuk pencarian ini saja. Koordinat tidak disimpan.'));
      const button=el('button','btn-location-action','Gunakan Lokasi Saya');button.type='button';
      button.addEventListener('click',()=>{
        if(busy) return;
        if(!navigator.geolocation) {row('Geolokasi tidak tersedia. Sebutkan kota melalui pesan.');return;}
        setBusy(true);button.textContent='Meminta lokasi…';
        navigator.geolocation.getCurrentPosition(pos=>{
          setBusy(false);button.textContent='Gunakan Lokasi Saya';
          const payload={latitude:pos.coords.latitude,longitude:pos.coords.longitude,facility_type:data.facility_type || null};
          request(form.dataset.locationUrl,payload,()=>button.click());
        },()=>{setBusy(false);button.textContent='Gunakan Lokasi Saya';row('Lokasi tidak dapat diakses. Anda tetap dapat mencari berdasarkan kota.');},{timeout:10000,enableHighAccuracy:false,maximumAge:0});
      });card.append(button);bubble.append(card);
    }
    if(Array.isArray(data.facilities) && data.facilities.length) {
      const list=el('div','facility-results-list');data.facilities.slice(0,5).forEach(f=>list.append(facilityCard(f)));bubble.append(list);
      const facilities=data.facilities.filter(hasCoords);
      if(facilities.length) {
        const mapElement=el('div','assistant-map');mapElement.setAttribute('aria-label','Peta fasilitas hasil pencarian');bubble.append(mapElement);
        if(typeof L==='undefined') mapElement.textContent='Peta tidak tersedia. Informasi fasilitas tetap dapat dibaca di atas.';
        else {
          mapElement.classList.add('skeleton');
          const map=L.map(mapElement).setView([facilities[0].latitude,facilities[0].longitude],12);maps.push(map);
          const tiles=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);
          const status=el('p','small muted','Memuat peta…');status.setAttribute('role','status');mapElement.after(status);
          tiles.on('load',()=>{mapElement.classList.remove('skeleton');status.textContent='';});tiles.on('tileerror',()=>{mapElement.classList.remove('skeleton');status.textContent='Sebagian peta gagal dimuat. Daftar fasilitas tetap tersedia.';});
          const points=facilities.map(f=>L.marker([f.latitude,f.longitude]).addTo(map).bindPopup(facilityCard(f)));
          if(data.user_location && hasCoords(data.user_location)) points.push(L.circleMarker([data.user_location.latitude,data.user_location.longitude],{radius:7,color:'#0B8179'}).addTo(map).bindPopup(el('strong','','Lokasi Anda')));
          map.fitBounds(L.featureGroup(points).getBounds(),{padding:[24,24],maxZoom:15});
        }
      }
    }
    messages.scrollTop=messages.scrollHeight;
  }
  form.addEventListener('submit',e=>{e.preventDefault();send(input.value);});
  input.addEventListener('input',resizeInput);
  input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();send(input.value);}});
  resizeInput();
  document.querySelectorAll('.suggested-pill').forEach(b=>b.addEventListener('click',()=>send(b.dataset.query)));
});
