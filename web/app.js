const $ = selector => document.querySelector(selector);
const form = $('#form');
const API_BASE = window.RIO_API_BASE || '/api/v1';
const labels = {
  busy: 'Заняты на эту дату',
  budget: 'Цена выше бюджета',
  format: 'Не берут этот формат',
  language: 'Не указан нужный язык',
  hours: 'Недостаточно часов на площадке'
};
let meta;
let previous = null;
let requestId = 0;

const escape = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
})[char]);
const money = value => new Intl.NumberFormat('ru-RU').format(value) + ' ₸';
const day = value => new Date(value + 'T12:00:00').toLocaleDateString('ru-RU', {day: 'numeric', month: 'long'});

function fill(query) {
  for (const [key, value] of Object.entries(query)) {
    if (form.elements[key]) form.elements[key].value = value ?? '';
  }
}
function legacyCard(p,i,q){return `<article class="card"><div class="card-top"><div class="avatar" aria-hidden="true">${escape(p.anon_name.split(' ').slice(0,2).map(x=>x[0]).join(''))}</div><div><h3>${escape(p.anon_name)}</h3><div class="meta">${escape(q.category)} · ${escape(p.city)} · № ${i+1}</div></div><div class="price">от ${money(p.price_from_kzt)}<small>за мероприятие</small></div></div><div class="why"><strong>ПОЧЕМУ В ПОДБОРКЕ</strong>${escape(p.explanation)}</div><p class="quote">Из описания профиля: «${escape(p.evidence)}»</p><div class="tags"><span class="tag">✓ Свободен ${escape(day(q.date))}</span><span class="tag">${escape(p.languages.join(' / '))}</span><span class="tag">${p.max_hours===null?'Без почасового присутствия':'До '+p.max_hours+' ч'}</span><span class="tag ${p.synthetic?'warning':''}">${p.synthetic?'Синтетический профиль':'Исходный анонимизированный профиль'}</span>${p.price_imputed?'<span class="tag warning">Цена проставлена в датасете</span>':''}${p.city_imputed?'<span class="tag warning">Город проставлен в датасете</span>':''}</div><details><summary>Подробнее о профиле и подборе</summary><p>${escape(p.description)}</p><p>Форматы: ${escape(p.event_formats.join(', '))}.</p><p>ID: ${escape(p.id)} · Балл текстовых совпадений: ${p.text_score}. ${q.preferences?(p.matched_terms.length?'Совпавшие основы слов: '+escape(p.matched_terms.join(', '))+'.':'Прямых совпадений слов с пожеланиями нет; обязательные условия выполнены.'):'Пожелания не заданы: порядок по цене, затем ID.'}</p></details></article>`;}
async function legacySearch(){
 if(!form.reportValidity())return;
 const id=++requestId,q=read(),button=$('.primary');button.disabled=true;$('#error').hidden=true;
 try{
  const response=await fetch('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(q)});
  const r=await response.json();if(!response.ok)throw new Error(r.error);if(id!==requestId)return;
  $('#timing').textContent=`${r.elapsed_ms.toFixed(1)} мс`;
  const audit=r.rejected.length?`<details class="audit"><summary>Почему исключены ${r.rejected.length} из ${r.pool_count} профилей?</summary><p>${Object.entries(r.exclusion_counts).map(([k,n])=>escape(labels[k])+': '+n).join(' · ')}. Один профиль может не пройти несколько условий.</p><ul>${r.rejected.map(p=>`<li>${escape(p.name)}: ${p.reasons.map(k=>escape(labels[k].toLowerCase())).join(', ')}.</li>`).join('')}</ul></details>`:'';
  const title=r.status==='matched'?'Ваша короткая подборка':r.status==='no_category'?'Такой категории пока нет':'На этих условиях не совпали';
  const empty=r.status==='matched'?'':`<div class="empty"><span>↗</span><h2>${r.status==='no_category'?'Попробуйте другой город':'Давайте изменим один параметр'}</h2><p>${r.status==='no_category'?'В каталоге нет сочетания выбранных города и категории. Изменение даты или бюджета этого не исправит.':'Условия не ослабляем автоматически. Посмотрите причины ниже: можно выбрать другую дату, бюджет, формат, язык или длительность.'}</p>${r.exclusion_counts.busy?'<button class="suggestion" id="next-date">Проверить следующий день →</button>':''}</div>`;
  const cards=r.cards.length?`<div class="card-deck" aria-label="Подобранные подрядчики">${r.cards.map((p,i)=>legacyCard(p,i,q)).join('')}</div>`:'';
  $('#results').innerHTML=`<div class="result-heading"><div><h2>${title}</h2><p>${escape(r.message)}</p></div><span class="pill">${escape(day(q.date))} · ${escape(q.city)}</span></div>${comparison(q,r)}${cards}${empty}${audit}<p class="form-note">Доступность — по учебному календарю датасета. Цена «от» не гарантирует окончательную смету.</p>`;
  document.querySelectorAll('.card-deck .card').forEach((item,index)=>{
    item.style.setProperty('--deck-index',index);
    item.tabIndex=0;
    item.addEventListener('click',()=>{document.querySelectorAll('.card-deck .card').forEach(card=>card.classList.remove('selected'));item.classList.add('selected');});
    item.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();item.click();}});
  });
  document.querySelector('.card-deck .card')?.classList.add('selected');
  previous={q,r};
  if($('#next-date'))$('#next-date').onclick=()=>{const date=new Date(q.date+'T12:00:00Z');date.setUTCDate(date.getUTCDate()+1);const next=date.toISOString().slice(0,10);if(next>meta.end){$('#error').textContent='Это последний день доступного календаря. Выберите более раннюю дату.';$('#error').hidden=false;return;}form.elements.date.value=next;search();};
 }catch(e){if(id===requestId){$('#error').textContent=e.message||'Не удалось связаться с сервером. Повторите запрос.';$('#error').hidden=false;}}finally{if(id===requestId)button.disabled=false;}
}

async function responseJson(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `Ошибка API (${response.status})`);
  return body;
}

function comparison(query, result) {
  if (!previous || previous.q.date === query.date) return '';
  const withoutDate = value => JSON.stringify(
    Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'date').sort())
  );
  if (withoutDate(query) !== withoutDate(previous.q)) return '';
  const busy = previous.r.cards.filter(profile => profile.busy_dates.includes(query.date));
  const newNames = result.cards
    .filter(profile => !previous.r.cards.some(old => old.id === profile.id))
    .map(profile => profile.anon_name);
  return `<div class="comparison"><strong>Что изменилось с ${escape(day(previous.q.date))} → ${escape(day(query.date))}</strong>${
    busy.length
      ? escape(busy.map(profile => profile.anon_name).join(', ')) + ' — теперь заняты и исключены.'
      : 'Никто из прежней тройки не занят; порядок может измениться из-за других освободившихся кандидатов.'
  }${newNames.length ? ' В подборке появились: ' + escape(newNames.join(', ')) + '.' : ''}</div>`;
}

function portfolio(profile) {
  const works = profile.top_works || [];
  if (!works.length) return '';
  const cards = works.map(work => {
    const rating = work.rating_count
      ? `★ ${Number(work.rating_average).toFixed(1)} · ${work.rating_count} оценок`
      : 'Новая работа · пока без оценок';
    const image = work.media_urls?.[0]
      ? `<a href="${escape(work.media_urls[0])}" target="_blank" rel="noopener"><img src="${escape(work.media_urls[0])}" alt="${escape(work.title)}" loading="lazy"></a>`
      : '<div class="work-placeholder" aria-hidden="true">✳</div>';
    return `<article class="work-card">${image}<div class="work-copy"><strong>${escape(work.title)}</strong><span class="work-rating">${escape(rating)}</span><p>${escape(work.description.slice(0, 180))}${work.description.length > 180 ? '…' : ''}</p><div class="rate-row" aria-label="Оценить работу от 1 до 5">${[1, 2, 3, 4, 5].map(score => `<button type="button" class="rate-work" data-work-id="${escape(work.id)}" data-score="${score}" aria-label="Поставить ${score}">${score}★</button>`).join('')}</div><span class="rating-status" data-rating-status="${escape(work.id)}"></span></div></article>`;
  }).join('');
  return `<section class="portfolio"><div class="portfolio-head"><strong>ЛУЧШИЕ РАБОТЫ</strong><span>${profile.published_work_count} опубликовано · по рейтингу клиентов</span></div><div class="work-list">${cards}</div></section>`;
}

function card(profile, index, query) {
  return `<article class="card"><div class="card-top"><div class="avatar" aria-hidden="true">${escape(profile.anon_name.split(' ').slice(0, 2).map(value => value[0]).join(''))}</div><div><h3>${escape(profile.anon_name)}</h3><div class="meta">${escape(query.category)} · ${escape(profile.city)} · № ${index + 1}</div></div><div class="price">от ${money(profile.price_from_kzt)}<small>за мероприятие</small></div></div><div class="why"><strong>ПОЧЕМУ В ПОДБОРКЕ</strong>${escape(profile.explanation)}</div><p class="quote">Из описания профиля: «${escape(profile.evidence)}»</p><div class="tags"><span class="tag">✓ Свободен ${escape(day(query.date))}</span><span class="tag">${escape(profile.languages.join(' / '))}</span><span class="tag">${profile.max_hours === null ? 'Без почасового присутствия' : 'До ' + profile.max_hours + ' ч'}</span><span class="tag ${profile.synthetic ? 'warning' : ''}">${profile.synthetic ? 'Синтетический профиль' : 'Исходный анонимизированный профиль'}</span>${profile.price_imputed ? '<span class="tag warning">Цена проставлена в датасете</span>' : ''}${profile.city_imputed ? '<span class="tag warning">Город проставлен в датасете</span>' : ''}</div>${portfolio(profile)}<details><summary>Подробнее о профиле и подборе</summary><p>${escape(profile.description)}</p><p>Форматы: ${escape(profile.event_formats.join(', '))}.</p><p>ID: ${escape(profile.id)} · Балл текстовых совпадений: ${profile.text_score}. ${query.preferences ? (profile.matched_terms.length ? 'Совпавшие основы слов: ' + escape(profile.matched_terms.join(', ')) + '.' : 'Прямых совпадений слов с пожеланиями нет; обязательные условия выполнены.') : 'Пожелания не заданы: порядок по цене, затем ID.'}</p></details></article>`;
}

function clientId() {
  let value = localStorage.getItem('rio_client_id');
  if (!value) {
    value = 'client_' + crypto.randomUUID().replaceAll('-', '');
    localStorage.setItem('rio_client_id', value);
  }
  return value;
}

function bindRatings() {
  document.querySelectorAll('.rate-work').forEach(button => {
    button.onclick = async () => {
      const workId = button.dataset.workId;
      const status = document.querySelector(`[data-rating-status="${CSS.escape(workId)}"]`);
      document.querySelectorAll(`[data-work-id="${CSS.escape(workId)}"]`).forEach(item => item.disabled = true);
      status.textContent = 'Сохраняем…';
      try {
        const response = await fetch(`${API_BASE}/works/${encodeURIComponent(workId)}/ratings`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({client_id: clientId(), score: Number(button.dataset.score)})
        });
        await responseJson(response);
        status.textContent = 'Спасибо, оценка учтена.';
        await search();
      } catch (error) {
        status.textContent = error.message || 'Не удалось сохранить оценку.';
        document.querySelectorAll(`[data-work-id="${CSS.escape(workId)}"]`).forEach(item => item.disabled = false);
      }
    };
  });
}

function bindCardDeck() {
  const deck = document.querySelector('.card-deck');
  if (!deck) return;
  const cards = [...deck.querySelectorAll('.card')];
  cards.forEach((item, index) => {
    item.style.setProperty('--deck-index', index);
    item.tabIndex = 0;
    item.addEventListener('click', () => {
      cards.forEach(cardItem => cardItem.classList.remove('selected'));
      item.classList.add('selected');
    });
    item.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        item.click();
      }
    });
  });
  cards[0]?.classList.add('selected');
  requestAnimationFrame(() => {
    deck.style.minHeight = `${Math.max(545, ...cards.map(item => item.scrollHeight + 48))}px`;
  });
}

async function search() {
  if (!form.reportValidity()) return;
  const id = ++requestId;
  const query = read();
  const button = $('.primary');
  button.disabled = true;
  $('#error').hidden = true;
  try {
    const response = await fetch(`${API_BASE}/recommendations`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(query)
    });
    const result = await responseJson(response);
    if (id !== requestId) return;
    $('#timing').textContent = `${result.elapsed_ms.toFixed(1)} мс`;
    const audit = result.rejected.length
      ? `<details class="audit"><summary>Почему исключены ${result.rejected.length} из ${result.pool_count} профилей?</summary><p>${Object.entries(result.exclusion_counts).map(([key, count]) => escape(labels[key]) + ': ' + count).join(' · ')}. Один профиль может не пройти несколько условий.</p><ul>${result.rejected.map(profile => `<li>${escape(profile.name)}: ${profile.reasons.map(key => escape(labels[key].toLowerCase())).join(', ')}.</li>`).join('')}</ul></details>`
      : '';
    const title = result.status === 'matched'
      ? 'Ваша короткая подборка'
      : result.status === 'no_category' ? 'Такой категории пока нет' : 'На этих условиях не совпали';
    const empty = result.status === 'matched' ? '' : `<div class="empty"><span>↗</span><h2>${result.status === 'no_category' ? 'Попробуйте другой город' : 'Давайте изменим один параметр'}</h2><p>${result.status === 'no_category' ? 'В каталоге нет сочетания выбранных города и категории. Изменение даты или бюджета этого не исправит.' : 'Условия не ослабляем автоматически. Посмотрите причины ниже: можно выбрать другую дату, бюджет, формат, язык или длительность.'}</p>${result.exclusion_counts.busy ? '<button class="suggestion" id="next-date">Проверить следующий день →</button>' : ''}</div>`;
    const cards = result.cards.length
      ? `<div class="card-deck" aria-label="Подобранные подрядчики">${result.cards.map((profile, index) => card(profile, index, query)).join('')}</div>`
      : '';
    $('#results').innerHTML = `<div class="result-heading"><div><h2>${title}</h2><p>${escape(result.message)}</p></div><span class="pill">${escape(day(query.date))} · ${escape(query.city)}</span></div>${comparison(query, result)}${cards}${empty}${audit}<p class="form-note">Доступность — по учебному календарю датасета. Цена «от» не гарантирует окончательную смету.</p>`;
    previous = {q: query, r: result};
    bindCardDeck();
    bindRatings();
    if ($('#next-date')) {
      $('#next-date').onclick = () => {
        const date = new Date(query.date + 'T12:00:00Z');
        date.setUTCDate(date.getUTCDate() + 1);
        const next = date.toISOString().slice(0, 10);
        if (next > meta.end) {
          $('#error').textContent = 'Это последний день доступного календаря. Выберите более раннюю дату.';
          $('#error').hidden = false;
          return;
        }
        form.elements.date.value = next;
        search();
      };
    }
  } catch (error) {
    if (id === requestId) {
      $('#error').textContent = error.message || 'Не удалось связаться с сервером. Повторите запрос.';
      $('#error').hidden = false;
    }
  } finally {
    if (id === requestId) button.disabled = false;
  }
}

form.onsubmit = event => {
  event.preventDefault();
  document.querySelectorAll('.demos button').forEach(button => button.classList.remove('active'));
  search();
};

$('#reset').onclick = () => {
  if (!meta) return;
  previous = null;
  fill(meta.demos[0].query);
  search();
};

async function init() {
  try {
    meta = await responseJson(await fetch(`${API_BASE}/meta`));
    for (const [name, key] of [['city', 'city'], ['category', 'categories'], ['event_format', 'event_formats'], ['language', 'languages']]) {
      for (const value of meta.options[key]) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        form.elements[name].append(option);
      }
    }
    $('#dataset-note').textContent = `HackAlem · ${meta.count} профилей · ${meta.synthetic} синтетических · Команда Rio`;
    meta.demos.forEach(demo => {
      const button = document.createElement('button');
      button.textContent = demo.label;
      button.onclick = () => {
        fill(demo.query);
        document.querySelectorAll('.demos button').forEach(item => item.classList.remove('active'));
        button.classList.add('active');
        search();
      };
      $('#demos').append(button);
    });
    fill(meta.demos[0].query);
    await search();
  } catch (error) {
    $('#error').textContent = error.message || 'Не удалось загрузить каталог.';
    $('#error').hidden = false;
  }
}

init();
