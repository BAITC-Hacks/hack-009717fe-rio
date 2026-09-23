const $ = s => document.querySelector(s);
const form = $('#form');
const labels = {busy:'Заняты на эту дату',budget:'Цена выше бюджета',format:'Не берут этот формат',language:'Не указан нужный язык',hours:'Недостаточно часов на площадке'};
let meta, previous = null, requestId = 0;
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = value => new Intl.NumberFormat('ru-RU').format(value) + ' ₸';
const day = value => new Date(value + 'T12:00:00').toLocaleDateString('ru-RU',{day:'numeric',month:'long'});
function fill(q){for(const [key,value] of Object.entries(q)) if(form.elements[key]) form.elements[key].value=value ?? '';}
function read(){const q=Object.fromEntries(new FormData(form));q.budget=Number(q.budget);q.hours=q.hours?Number(q.hours):null;return q;}
function comparison(q,r){
  if(!previous || previous.q.date===q.date)return '';
  const withoutDate = value => JSON.stringify(Object.fromEntries(Object.entries(value).filter(([k])=>k!=='date').sort()));
  if(withoutDate(q)!==withoutDate(previous.q))return '';
  const busy = previous.r.cards.filter(p=>p.busy_dates.includes(q.date));
  const newNames=r.cards.filter(p=>!previous.r.cards.some(old=>old.id===p.id)).map(p=>p.anon_name);
  return `<div class="comparison"><strong>Что изменилось с ${escape(day(previous.q.date))} → ${escape(day(q.date))}</strong>${busy.length?escape(busy.map(p=>p.anon_name).join(', '))+' — теперь заняты и исключены.':'Никто из прежней тройки не занят; порядок может измениться из-за других освободившихся кандидатов.'}${newNames.length?' В подборке появились: '+escape(newNames.join(', '))+'.':''}</div>`;
}
function card(p,i,q){return `<article class="card"><div class="card-top"><div class="avatar" aria-hidden="true">${escape(p.anon_name.split(' ').slice(0,2).map(x=>x[0]).join(''))}</div><div><h3>${escape(p.anon_name)}</h3><div class="meta">${escape(q.category)} · ${escape(p.city)} · № ${i+1}</div></div><div class="price">от ${money(p.price_from_kzt)}<small>за мероприятие</small></div></div><div class="why"><strong>ПОЧЕМУ В ПОДБОРКЕ</strong>${escape(p.explanation)}</div><p class="quote">Из описания профиля: «${escape(p.evidence)}»</p><div class="tags"><span class="tag">✓ Свободен ${escape(day(q.date))}</span><span class="tag">${escape(p.languages.join(' / '))}</span><span class="tag">${p.max_hours===null?'Без почасового присутствия':'До '+p.max_hours+' ч'}</span><span class="tag ${p.synthetic?'warning':''}">${p.synthetic?'Синтетический профиль':'Исходный анонимизированный профиль'}</span>${p.price_imputed?'<span class="tag warning">Цена проставлена в датасете</span>':''}${p.city_imputed?'<span class="tag warning">Город проставлен в датасете</span>':''}</div><details><summary>Подробнее о профиле и подборе</summary><p>${escape(p.description)}</p><p>Форматы: ${escape(p.event_formats.join(', '))}.</p><p>ID: ${escape(p.id)} · Балл текстовых совпадений: ${p.text_score}. ${q.preferences?(p.matched_terms.length?'Совпавшие основы слов: '+escape(p.matched_terms.join(', '))+'.':'Прямых совпадений слов с пожеланиями нет; обязательные условия выполнены.'):'Пожелания не заданы: порядок по цене, затем ID.'}</p></details></article>`;}
async function search(){
 if(!form.reportValidity())return;
 const id=++requestId,q=read(),button=$('.primary');button.disabled=true;$('#error').hidden=true;
 try{
  const response=await fetch('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(q)});
  const r=await response.json();if(!response.ok)throw new Error(r.error);if(id!==requestId)return;
  $('#timing').textContent=`${r.elapsed_ms.toFixed(1)} мс`;
  const audit=r.rejected.length?`<details class="audit"><summary>Почему исключены ${r.rejected.length} из ${r.pool_count} профилей?</summary><p>${Object.entries(r.exclusion_counts).map(([k,n])=>escape(labels[k])+': '+n).join(' · ')}. Один профиль может не пройти несколько условий.</p><ul>${r.rejected.map(p=>`<li>${escape(p.name)}: ${p.reasons.map(k=>escape(labels[k].toLowerCase())).join(', ')}.</li>`).join('')}</ul></details>`:'';
  const title=r.status==='matched'?'Ваша короткая подборка':r.status==='no_category'?'Такой категории пока нет':'На этих условиях не совпали';
  const empty=r.status==='matched'?'':`<div class="empty"><span>↗</span><h2>${r.status==='no_category'?'Попробуйте другой город':'Давайте изменим один параметр'}</h2><p>${r.status==='no_category'?'В каталоге нет сочетания выбранных города и категории. Изменение даты или бюджета этого не исправит.':'Условия не ослабляем автоматически. Посмотрите причины ниже: можно выбрать другую дату, бюджет, формат, язык или длительность.'}</p>${r.exclusion_counts.busy?'<button class="suggestion" id="next-date">Проверить следующий день →</button>':''}</div>`;
  const cards=r.cards.length?`<div class="card-deck" aria-label="Подобранные подрядчики">${r.cards.map((p,i)=>card(p,i,q)).join('')}</div>`:'';
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
form.onsubmit=e=>{e.preventDefault();document.querySelectorAll('.demos button').forEach(b=>b.classList.remove('active'));search();};
$('#reset').onclick=()=>{if(!meta)return;previous=null;fill(meta.demos[0].query);search();};
async function init(){try{const response=await fetch('/api/meta');if(!response.ok)throw new Error('Не удалось загрузить каталог.');meta=await response.json();for(const [name,key] of [['city','city'],['category','categories'],['event_format','event_formats'],['language','languages']]){for(const value of meta.options[key]){const option=document.createElement('option');option.value=value;option.textContent=value;form.elements[name].append(option);}}$('#dataset-note').textContent=`HackAlem · ${meta.count} профилей · ${meta.synthetic} синтетических · Команда Rio`;meta.demos.forEach((demo,i)=>{const b=document.createElement('button');b.textContent=demo.label;b.onclick=()=>{fill(demo.query);document.querySelectorAll('.demos button').forEach(x=>x.classList.remove('active'));b.classList.add('active');search();};$('#demos').append(b);});fill(meta.demos[0].query);await search();}catch(e){$('#error').textContent=e.message;$('#error').hidden=false;}}
init();
