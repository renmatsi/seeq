"use strict";

const get = selector => document.querySelector(selector);
const all = selector => [...document.querySelectorAll(selector)];
const icons = {
  settings:'<path d="M10 3h4l.5 2.2 1.6.9 2.2-.7 2 3.5-1.7 1.6v2l1.7 1.6-2 3.5-2.2-.7-1.6.9L14 21h-4l-.5-2.2-1.6-.9-2.2.7-2-3.5 1.7-1.6v-2L3.7 9.9l2-3.5 2.2.7 1.6-.9z"/><circle cx="12" cy="12" r="3"/>',
  minus:'<path d="M5 12h14"/>',
  plus:'<path d="M5 12h14m-7-7v14"/>',
  close:'<path d="m6 6 12 12M18 6 6 18"/>',
  check:'<path d="m5 12 5 5L19 7"/>',
  reset:'<path d="M4 10a8 8 0 1 1 2 8M4 5v5h5"/>',
  stop:'<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/>',
  flask:'<path d="M9 3h6m-5 0v6l-5 8.5A2 2 0 0 0 6.7 21h10.6a2 2 0 0 0 1.7-3.5L14 9V3m-6 11h8"/>',
  "panel-right":'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M15 5v14"/>',
  torrent:'<path d="M8 3h5l5 5v11a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm5 0v5h5m-6 3v6m-2.5-2.5L12 17l2.5-2.5"/>',
  external:'<path d="M13 5h6v6m0-6-9 9m7 0v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h4"/>',
  unavailable:'<circle cx="12" cy="12" r="8"/><path d="m6.3 6.3 11.4 11.4"/>',
  save:'<path d="M5 3h12l4 4v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm2 0v5h9V3m-9 18v-8h10v8"/>',
  sort:'<path d="M4 6h10M4 11h8M4 16h6m8-10v12m-3-3 3 3 3-3"/>',
  log:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6m-6 4h6m-6 4h4"/>',
  search:'<circle cx="10.7" cy="10.7" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  star:'<path d="m12 3 2.7 5.7 6.3.8-4.6 4.4 1.2 6.3-5.6-3-5.6 3 1.2-6.3L3 9.5l6.3-.8z"/>',
  history:'<path d="M3 11a9 9 0 1 1 2 7M3 6v5h5m4-4v5l3 2"/>',
  trash:'<path d="M4 7h16M9 7V4h6v3m3 0-.8 13H6.8L6 7m4 4v5m4-5v5"/>',
  radio:'<circle cx="12" cy="12" r="1.7"/><path d="M8.7 8.6a4.7 4.7 0 0 0 0 6.8m6.6-6.8a4.7 4.7 0 0 1 0 6.8M5.6 5.7a8.7 8.7 0 0 0 0 12.6m12.8-12.6a8.7 8.7 0 0 1 0 12.6"/>',
  magnet:'<path d="m4 11 5.4-5.4a6.2 6.2 0 0 1 8.8 8.8l-5.4 5.4-3-3 5.4-5.4a2 2 0 0 0-2.8-2.8L7 14zm2.2-2.2 3 3m2.8 2.9 3 3"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || ""}</svg>`;
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const bridge = window.chrome?.webview;
const send = (action, data={}) => bridge?.postMessage({action,...data});
const searchForm = get("#search");
const filterForm = get("#filters");
const filterToggle = get("#filter-toggle");
const sort = get("#sort");
const sortToggle = sort.querySelector("summary");
const dialog = get("#dialog");
const dialogContent = get("#dialog-content");
const backdropHost = document.body;
const logToggle = get("#log-toggle");
const statusAnnouncement = get("#status");
const logEntries = [];
const query = get("#query");
let format = new Intl.NumberFormat(locale);
const field = name => filterForm.elements.namedItem(name);
const themes = {"Sistema":"system","Papel":"paper","Grafite":"graphite","Meia-noite":"midnight","AMOLED":"amoled"};
const accents = {"Azul":"#3478ff","Violeta":"#9a5bff","Verde":"#22d482","Âmbar":"#ffad24","Rosa":"#ff4a90","Ciano":"#00bfdc"};
const presets = {"Sistema":accents.Azul,"Papel":accents.Âmbar,"Grafite":accents.Azul,"Meia-noite":accents.Ciano,"AMOLED":accents.Azul};
const blends = {"auto":"Automático","soft-light":"Luz suave","screen":"Tela","multiply":"Multiplicar"};
const backdropDefaults = {backdrop:false,blend:"auto",backdropOpacity:14};
const legacyAccents = {
  "#0059ff":accents.Azul, "#8253d6":accents.Violeta, "#218869":accents.Verde,
  "#b46c12":accents.Âmbar, "#c34d78":accents.Rosa, "#168394":accents.Ciano
};
const validColor = value => typeof value==="string" && /^#[0-9a-f]{6}$/i.test(value);
const modes = matchMedia("(prefers-color-scheme:light)");
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
let appearance = {theme:"Grafite", accent:presets.Grafite, ...backdropDefaults};
let appliedPalette;
let state = {rows:[],total:0,view:"Busca",filters:{},sources:[],history:[],facets:{},failures:{}};
let selected = "";
let details = true;
let lastStatus;
let canDragNative = true;
let editFilters = false;
let closeFiltersOnState = false;
let ready = false;

const rgb = hex => [1,3,5].map(index=>parseInt(hex.slice(index,index+2),16));
const mix = (from,to,amount) => from.map((channel,index)=>channel+(to[index]-channel)*amount);
const luminance = color => color.map(channel=>channel/255)
  .map(channel=>channel<=.04045?channel/12.92:((channel+.055)/1.055)**2.4)
  .reduce((sum,channel,index)=>sum+channel*[.2126,.7152,.0722][index],0);
const contrast = (a,b) => (Math.max(a,b)+.05)/(Math.min(a,b)+.05);

function accentInk(color, background, light) {
  const endpoint = light ? [0,0,0] : [255,255,255];
  let tone = color;
  for (let step=1; contrast(luminance(tone),background)<4.5 && step<=20; step++) {
    tone = mix(color,endpoint,step/20).map(Math.round);
  }
  return `rgb(${tone.join(" ")})`;
}

function palette() {
  const root = document.documentElement;
  const theme = themes[appearance.theme] || "graphite";
  const light = theme==="paper" || (theme==="system" && modes.matches);
  backdropHost.toggleAttribute("data-backdrop",appearance.backdrop);
  backdropHost.style.setProperty("--backdrop-strength",String(appearance.backdropOpacity/100));
  const blend = appearance.blend==="auto" ? (light?"multiply":"screen") : appearance.blend;
  backdropHost.style.setProperty("--backdrop-blend",blend);
  const key = `${theme}/${light}/${appearance.accent}`;
  if (key===appliedPalette) return;
  appliedPalette = key;
  root.dataset.theme = theme;
  root.dataset.light = String(light);
  const solid = rgb(appearance.accent);
  const styles = getComputedStyle(root);
  const backgrounds = ["--base","--paper","--surface","--hover"].map(name=>rgb(styles.getPropertyValue(name).trim()));
  backgrounds.push(mix(backgrounds[1],solid,.17));
  const levels = backgrounds.map(luminance);
  const background = light ? Math.min(...levels) : Math.max(...levels);
  const fill = luminance(solid);
  root.style.setProperty("--accent",appearance.accent);
  root.style.setProperty("--accent-text",accentInk(solid,background,light));
  root.style.setProperty("--on-accent",contrast(fill,0)>=contrast(fill,1)?"#000":"#fff");
}

function fadeIn(element) {
  if (!reduceMotion.matches) element.animate([{opacity:.58},{opacity:1}], {duration:160,easing:"ease-out"});
}

function button(label, id, kind, symbol, primary=false, itemTitle="") {
  const title = tr(label);
  const accessibleName = itemTitle ? `${title} · ${itemTitle}` : title;
  return `<button type="button" class="icon-button${primary?" primary":""}" data-open="${esc(id)}" data-kind="${kind}"
    aria-label="${esc(accessibleName)}" title="${esc(title)}">${icon(symbol)}</button>`;
}

function resultLink(row) {
  if (row.magnet) return button("Abrir magnet no cliente BitTorrent",row.id,"magnet","magnet",false,row.title);
  if (row.torrent) return button("Abrir .torrent",row.id,"torrent","torrent",false,row.title);
  if (row.page) return button("Abrir publicação",row.id,"page","external",false,row.title);
  const label = esc(tr("Nenhum link disponível"));
  return `<span class="link-unavailable" role="img" aria-label="${label}" title="${label}">${icon("unavailable")}</span>`;
}

function nameButton(button, label) {
  button.setAttribute("aria-label", tr(label));
  button.title = tr(label);
}

function showAdvancedFilters(open) {
  filterForm.hidden = !open;
  filterForm.inert = !open;
  filterToggle.setAttribute("aria-expanded", String(open));
  nameButton(filterToggle, open ? "Recolher busca avançada" : "Abrir busca avançada");
  filterToggle.innerHTML = icon(open ? "minus" : "plus");
}

function showRows() {
  const current = state.rows.find(row=>row.id===selected) || state.rows[0];
  selected = current?.id || "";
  const emptyMessage = state.view==="Favoritos" ? "Os resultados salvos aparecem aqui."
    : state.running ? "Aguardando as primeiras fontes…"
    : state.query ? "Nenhum resultado com os critérios atuais." : "";
  get("#results").innerHTML = state.rows.map(row=>`
    <div class="result">
      <button type="button" class="result-main" data-row="${esc(row.id)}" aria-pressed="${row.id===selected}">
        <span><strong>${esc(row.title)}</strong><span class="source">${esc(row.source.replaceAll(", "," · "))}</span></span>
        <span class="file">${esc(row.size)}${row.format?" · "+esc(row.format):""}<br>${esc(row.published==="—"?tr("Data não informada"):row.published)}</span>
        <span class="seeds">${esc(row.seeders==null?tr("Sem dados"):tr("{count} seeds",{count:format.format(row.seeders)}))}</span>
      </button>
      ${resultLink(row)}
    </div>`).join("") || (emptyMessage ? `<p class="empty">${esc(tr(emptyMessage))}</p>` : "");
  const panel = get("#details");
  panel.hidden = !details || !current;
  get("#toggle-detail").hidden = !current;
  get("#result-summary").hidden = get("#count").hidden && !current;
  get("#split").classList.toggle("no-details",!details || !current);
  if (!current) return;
  const meta = [current.category,current.language,current.quality,current.format,current.size==="—"?"":current.size].filter(Boolean).map(value=>tr(value));
  const favoriteTip = current.favorite ? "Remover dos favoritos" : "Adicionar aos favoritos";
  const actions = [
    current.torrent?button("Abrir .torrent",current.id,"torrent","torrent",true):"",
    current.magnet&&!current.torrent?button("Abrir magnet",current.id,"magnet","magnet",true):"",
    current.page?button("Abrir publicação",current.id,"page","external",!current.torrent&&!current.magnet):"",
    `<button type="button" class="icon-button" data-favorite="${esc(current.id)}" aria-pressed="${Boolean(current.favorite)}"
      aria-label="${esc(tr("Favorito"))}" title="${esc(tr(favoriteTip))}">${icon("star")}</button>`
  ];
  panel.innerHTML = `<h2>${esc(current.title)}</h2>
    ${meta.length?`<p class="muted">${esc(meta.join(" · "))}</p>`:""}
    <p>${esc(tr("Encontrado em"))} <strong>${esc(current.source.replaceAll(", "," · "))}</strong></p>
    <p>${esc(tr("Publicação"))}: <strong>${esc(current.published==="—"?tr("Data não informada"):current.published)}</strong>${current.year?` · ${esc(tr("Ano do conteúdo"))}: ${esc(current.year)}`:""}</p>
    <p class="muted">${esc(current.seeders==null?tr("Seeders não informados"):tr("{count} seeders informados",{count:format.format(current.seeders)}))}</p>
    <div class="detail-actions">${actions.join("")}</div>`;
}

function dateFields() {
  all("[data-date]").forEach(label=>{
    label.hidden = field("period").value!=="custom";
    label.querySelector("input").disabled = label.hidden;
  });
  field("unknown_dates").disabled = !field("period").value;
}

function translateChip(key, value, filters) {
  if (locale==="pt-BR") return value;
  if (key==="year" && filters.year) return tr("Ano {year}",{year:filters.year});
  if (key==="period") {
    if (filters.period==="custom") {
      const {from_date:from,to_date:to} = filters;
      if (from && to) return `${from} – ${to}`;
      if (from) return tr("Desde {date}",{date:from});
      if (to) return tr("Até {date}",{date:to});
    }
    if (/^\d+$/.test(filters.period) && filters.period!=="1") return tr("Últimos {days} dias",{days:filters.period});
  }
  return tr(value);
}

function syncFilters() {
  for (const [key,value] of Object.entries(state.filters || {})) {
    const input = field(key);
    if (!input) continue;
    if (input.type==="checkbox") { input.checked=Boolean(value); continue; }
    const selected = value==null?"":String(value);
    if (state.facets[key]) {
      const items = state.facets[key];
      input.replaceChildren(new Option(tr("Qualquer"),""),...items.map(([name,count])=>new Option(`${tr(name)} (${format.format(count)})`,name)));
      if (selected&&!items.some(([name])=>name===selected)) input.add(new Option(tr(selected),selected));
    }
    if (key==="period" && selected && ![...input.options].some(option=>option.value===selected)) {
      input.add(new Option(tr("Últimos {days} dias",{days:selected}),selected));
    }
    input.value = selected;
  }
  dateFields();
}

function showIssues() {
  const problems = Object.entries(state.failures || {});
  const panel = get("#issues");
  panel.hidden = !problems.length;
  panel.innerHTML = problems.map(([name,message])=>`<p><strong>${esc(name)}</strong> · ${esc(translateStatus(message))}
    ${["EXT.to","1337x"].includes(name)?`<button data-manual="${esc(name)}"${state.running?" disabled":""}>${esc(tr("Abrir fonte"))}</button>`:""}</p>`).join("");
}

function render() {
  const isSearch = state.view==="Busca";
  backdropHost.toggleAttribute("data-results",Boolean(state.rows.length));
  searchForm.hidden = !isSearch;
  get("#view-title").hidden = isSearch;
  all("[data-view]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.view===state.view)));
  const count = get("#count");
  count.hidden = isSearch && (!state.query || state.running);
  count.textContent = count.hidden ? "" : tr(state.rows.length===1?"{count} resultado":"{count} resultados",{count:format.format(state.rows.length)});
  syncSearchButton();
  get("#cancel-search").hidden=!state.running;
  const order = state.order || "Relevância";
  sortToggle.title = `${tr("Ordenar resultados")} · ${tr(order)}`;
  sort.querySelectorAll("[data-order]").forEach(option=>option.setAttribute("aria-pressed",String(option.dataset.order===order)));
  all("[data-period]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.period===(state.filters.period||""))));
  get("#chips").innerHTML=(state.chips||[]).map(([key,value])=>{
    const label = translateChip(key,value,state.filters);
    const remove = esc(tr("Remover {item}",{item:label}));
    return `<button data-remove="${esc(key)}" aria-label="${remove}" title="${remove}">${esc(label)} ${icon("close")}</button>`;
  }).join("");
  get("#interpreted").textContent=state.inferred?.length?tr("{count} filtro(s) interpretado(s)",{count:format.format(state.inferred.length)}):"";
  if (!editFilters) syncFilters();
  showIssues();
  showRows();
}

function showLog() {
  dialogContent.innerHTML = logEntries.length
    ? `<ol class="log-list">${logEntries.map(({time,message})=>`<li><time>${esc(time.toLocaleTimeString(locale))}</time><span>${esc(translateStatus(message))}</span></li>`).join("")}</ol>`
    : `<p class="muted">${esc(tr("Nenhuma atividade nesta sessão."))}</p>`;
}

function recordStatus(message, attention=false) {
  if (!message) return;
  statusAnnouncement.textContent = translateStatus(message);
  const time = new Date();
  logEntries.unshift({time,message});
  if (logEntries.length > 60) logEntries.pop();
  if (dialog.open && dialog.dataset.panel === "log") showLog();
  else if (attention) logToggle.setAttribute("data-unread","");
}

function showHistory() {
  const entries = state.history.filter(term=>typeof term==="string" && term).slice().reverse();
  if (!entries.length) {
    dialogContent.innerHTML = `<p class="muted">${esc(tr("Nenhuma busca salva."))}</p>`;
    return;
  }
  dialogContent.innerHTML = `<div class="history-actions">
      <button type="button" class="history-clear" data-confirm-clear>${icon("trash")}${esc(tr("Limpar histórico"))}</button>
      <div class="history-confirm" data-clear-history-prompt hidden>
        <p>${esc(tr("Limpar todo o histórico?"))}</p>
        <button type="button" data-cancel-clear>${esc(tr("Cancelar"))}</button>
        <button type="button" class="primary" data-clear-history>${esc(tr("Limpar tudo"))}</button>
      </div>
    </div>
    <div class="history-list">${entries.map(term=>{
      const value = esc(term);
      return `<div class="history-item">
        <button type="button" class="history-query" data-history="${value}">${value}</button>
        <button type="button" class="icon-button" data-history-remove="${value}"
          aria-label="${esc(tr("Remover {item} do histórico",{item:term}))}" title="${esc(tr("Remover do histórico"))}">${icon("trash")}</button>
      </div>`;
    }).join("")}</div>`;
}

function confirmHistoryClear(show) {
  const trigger = dialogContent.querySelector("[data-confirm-clear]");
  const prompt = dialogContent.querySelector("[data-clear-history-prompt]");
  trigger.hidden = show;
  prompt.hidden = !show;
  (show ? prompt.querySelector("[data-cancel-clear]") : trigger).focus();
}

function openPanel(type) {
  dialog.dataset.panel=type;
  get("#dialog-title").textContent=tr({appearance:"Configurações",history:"Histórico",sources:"Fontes",log:"Log de atividade"}[type]);
  if (type==="log") {
    logToggle.removeAttribute("data-unread");
    showLog();
  } else if (type==="appearance") {
    dialogContent.innerHTML=`<div class="panel-section"><label class="language-setting">${esc(tr("Idioma da interface"))}
      <select data-locale>${Object.entries(locales).map(([value,label])=>`<option value="${value}" lang="${value}"${locale===value?" selected":""}>${esc(label)}</option>`).join("")}</select>
      </label></div>
      <div class="panel-section"><h3>${esc(tr("Esquema de cores"))}</h3><div class="panel-options">
      ${Object.keys(themes).map(name=>`<button data-theme-choice="${name}" aria-pressed="${appearance.theme===name}">${esc(tr(name))}</button>`).join("")}
      </div></div><div class="panel-section"><h3>${esc(tr("Cor de destaque"))}</h3><div class="panel-options">
      ${Object.entries(accents).map(([name,hex])=>`<button class="accent-option" data-accent="${hex}" aria-pressed="${appearance.accent===hex}"><span class="swatch" style="--swatch:${hex}"></span>${esc(tr(name))}</button>`).join("")}
      </div><label class="color-custom"><input type="color" data-color value="${appearance.accent}">${esc(tr("Cor personalizada"))}</label></div>
      <div class="panel-section">
        <label class="backdrop-toggle"><input type="checkbox" data-backdrop-toggle${appearance.backdrop?" checked":""}> ${esc(tr("Fundo ilustrado"))}</label>
        <div class="backdrop-options" data-backdrop-controls${appearance.backdrop?"":" hidden"}>
          <label>${esc(tr("Modo de mistura"))}<select data-blend>
            ${Object.entries(blends).map(([value,label])=>`<option value="${value}"${appearance.blend===value?" selected":""}>${esc(tr(label))}</option>`).join("")}
          </select></label>
          <label><span>${esc(tr("Intensidade"))} <output data-opacity-label>${appearance.backdropOpacity}%</output></span>
            <input type="range" min="5" max="30" value="${appearance.backdropOpacity}" data-opacity>
          </label>
        </div>
      </div>`;
  } else if (type==="history") {
    showHistory();
  } else if (type==="sources") {
    dialogContent.innerHTML=`<form id="sources-form"><div class="source-grid">${state.sources.map(item=>`<label>
      <input type="checkbox" name="source" value="${esc(item.key)}"${item.enabled?" checked":""}>${esc(item.name)}</label>`).join("")}
      <label class="muted">BitTorrented · ${esc(tr("acesso por convite"))}</label></div>
      <div class="source-auth"><label>${esc(tr("Porta Jackett"))}<input name="port" type="number" value="${esc(state.jackettPort||9117)}" min="1" max="65535" required></label>
      <label>${esc(tr("Chave do Jackett"))}<input name="apiKey" type="password" placeholder="${esc(tr(state.jackettReady?"Chave ativa nesta sessão":"Somente nesta sessão"))}"></label></div>
      <p class="muted">${esc(tr("Use o Jackett local para RuTracker e CGPeers. Ative somente fontes e plugins autorizados."))}</p>
      <div class="panel-bottom"><button type="submit" class="icon-button primary" aria-label="${esc(tr("Salvar fontes"))}" title="${esc(tr("Salvar fontes"))}">${icon("save")}</button></div></form>`;
    get("#sources-form").addEventListener("submit",event=>{
      event.preventDefault();
      const values=new FormData(event.target);
      const checked=new Set(values.getAll("source"));
      send("sources",{enabled:Object.fromEntries(state.sources.map(item=>[item.key,checked.has(item.key)])),
        port:Number(values.get("port")),apiKey:values.get("apiKey")});
      dialog.close();
    });
  }
  if (!dialog.open) dialog.showModal();
}

function updateAppearance(save) {
  palette();
  if (save) send("appearance",appearance);
}

function updateLanguage(value) {
  setLocale(value);
  format = new Intl.NumberFormat(locale);
  nameButton(filterToggle,filterForm.hidden?"Abrir busca avançada":"Recolher busca avançada");
  nameButton(get("#toggle-detail"),details?"Recolher detalhes":"Mostrar detalhes");
}

function search() {
  if (state.browserOpen||(state.running&&query.value.trim()===state.query)) return;
  if (!query.value.trim()) { query.focus(); return; }
  selected="";
  send("search",{query:query.value,smart:get("#smart").checked});
}

function syncSearchButton() {
  searchForm.toggleAttribute("data-searching",Boolean(state.running));
  searchForm.querySelector("button").disabled=state.browserOpen||(state.running&&query.value.trim()===state.query);
}

for (const node of all("[data-icon]")) node.innerHTML=icon(node.dataset.icon);
searchForm.addEventListener("submit",event=>{event.preventDefault();search();});
query.addEventListener("input",syncSearchButton);
get("#cancel-search").addEventListener("click",()=>send("cancel"));
get("#search-example").addEventListener("click",()=>{
  get("#smart").checked=true;
  query.value="linux iso últimos 7 dias até 3 GB";
  showAdvancedFilters(false);
  query.focus();
  search();
});
field("period").addEventListener("change",dateFields);
filterForm.addEventListener("input",event=>{if (event.target.name) editFilters=true;});
filterForm.addEventListener("submit",event=>{
  event.preventDefault();
  const values=Object.fromEntries(new FormData(filterForm));
  values.unknown_dates=field("unknown_dates").checked;
  closeFiltersOnState=true;
  send("filters",{values});
});
filterToggle.addEventListener("click",()=>{
  const opening = filterForm.hidden;
  showAdvancedFilters(opening);
  if (opening && !editFilters) syncFilters();
});
get("#toggle-detail").addEventListener("click",event=>{
  details=!details;
  event.currentTarget.setAttribute("aria-expanded",String(details));
  nameButton(event.currentTarget, details ? "Recolher detalhes" : "Mostrar detalhes");
  showRows();
});
dialog.addEventListener("input",event=>{
  if (event.target.matches("[data-color]")&&validColor(event.target.value)) {
    appearance.accent=event.target.value;
    updateAppearance(false);
    dialog.querySelectorAll("[data-accent]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.accent===appearance.accent)));
  } else if (event.target.matches("[data-opacity]")) {
    appearance.backdropOpacity = event.target.valueAsNumber;
    dialog.querySelector("[data-opacity-label]").value = `${appearance.backdropOpacity}%`;
    updateAppearance(false);
  }
});
dialog.addEventListener("change",event=>{
  const target = event.target;
  if (target.matches("[data-locale]")) {
    updateLanguage(target.value);
    render();
    openPanel("appearance");
    dialog.querySelector("[data-locale]").focus();
    send("locale",{locale});
    return;
  }
  if (target.matches("[data-backdrop-toggle]")) {
    appearance.backdrop = target.checked;
    dialog.querySelector("[data-backdrop-controls]").hidden = !appearance.backdrop;
  } else if (target.matches("[data-blend]")) {
    appearance.blend = target.value;
  } else if (!target.matches("[data-color],[data-opacity]")) return;
  updateAppearance(true);
});
get("#titlebar").addEventListener("pointerdown",event=>{
  if (!canDragNative&&event.button===0&&!event.target.closest("button")) send("drag");
});
document.addEventListener("keydown",event=>{
  if (event.key==="Escape" && sort.open && !dialog.open) {
    sort.open=false;
    sortToggle.focus();
  }
  if (event.ctrlKey&&event.key.toLowerCase()==="k") {event.preventDefault();query.focus();}
  if (event.altKey&&event.key==="Enter"&&selected&&state.rows.find(row=>row.id===selected)?.magnet) {
    event.preventDefault();send("open",{id:selected,kind:"magnet"});
  }
});
document.addEventListener("click",event=>{
  if (!sort.contains(event.target)) sort.open=false;
  const button=event.target.closest("button");
  if (!button) return;
  const d=button.dataset;
  if (d.window) send(d.window);
  else if (d.panel) openPanel(d.panel);
  else if (d.view) {selected="";send("view",{view:d.view});}
  else if (d.order) {sort.open=false;sortToggle.focus();send("sort",{order:d.order});}
  else if (d.period!==undefined) {editFilters=false;send("period",{period:d.period});}
  else if (d.remove) {editFilters=false;send("remove",{key:d.remove});}
  else if (d.row) {
    const changed = selected!==d.row;
    selected=d.row;showRows();
    if (details && changed) fadeIn(get("#details"));
    [...get("#results").querySelectorAll("[data-row]")].find(node=>node.dataset.row===selected)?.focus({preventScroll:true});
  }
  else if (d.open) send("open",{id:d.open,kind:d.kind});
  else if (d.favorite) send("favorite",{id:d.favorite});
  else if (d.manual) send("manual",{query:query.value,source:d.manual});
  else if (d.history) {query.value=d.history;dialog.close();search();}
  else if (d.historyRemove) send("history-remove",{query:d.historyRemove});
  else if (button.hasAttribute("data-confirm-clear")) confirmHistoryClear(true);
  else if (button.hasAttribute("data-cancel-clear")) confirmHistoryClear(false);
  else if (button.hasAttribute("data-clear-history")) send("history-clear");
  else if (d.themeChoice&&d.themeChoice in themes) {
    appearance={...appearance,theme:d.themeChoice,accent:presets[d.themeChoice]};updateAppearance(true);openPanel("appearance");
    dialog.querySelector(`[data-theme-choice="${d.themeChoice}"]`)?.focus();
  }
  else if (d.accent&&validColor(d.accent)) {
    appearance.accent=d.accent;updateAppearance(true);openPanel("appearance");
    dialog.querySelector(`[data-accent="${d.accent}"]`)?.focus();
  }
  else if (button.hasAttribute("data-clear")) {editFilters=false;send("clear");}
  else if (button.hasAttribute("data-dialog-close")) dialog.close();
});
modes.addEventListener("change",palette);

bridge?.addEventListener("message",event=>{
  const next=event.data;
  if (next.type==="window") {canDragNative=Boolean(next.nativeDrag);return;}
  if (next.type==="status") {
    closeFiltersOnState=false;
    recordStatus(next.message,true);
    return;
  }
  if (next.type!=="state") return;
  const previous = state;
  state=next;
  if (!ready) updateLanguage(next.locale);
  if (lastStatus !== undefined && next.status !== lastStatus) recordStatus(next.status);
  lastStatus = next.status;
  if (closeFiltersOnState) {
    const restoreFocus = filterForm.contains(document.activeElement);
    showAdvancedFilters(false);editFilters=false;closeFiltersOnState=false;
    if (restoreFocus) filterToggle.focus();
  }
  const saved=next.appearance||{};
  if (!ready && Object.hasOwn(themes,saved.theme) && validColor(saved.accent)) {
    const color = saved.accent.toLowerCase();
    const opacity = saved.backdropOpacity;
    appearance = {
      theme:saved.theme, accent:legacyAccents[color] || color, backdrop:saved.backdrop===true,
      blend:Object.hasOwn(blends,saved.blend)?saved.blend:backdropDefaults.blend,
      backdropOpacity:Number.isInteger(opacity)&&opacity>=5&&opacity<=30?opacity:backdropDefaults.backdropOpacity
    };
    palette();
  }
  render();
  if (dialog.open && dialog.dataset.panel==="history" &&
    (next.history.length!==previous.history.length || next.history.some((term,index)=>term!==previous.history[index]))) {
    const restoreFocus = dialogContent.contains(document.activeElement);
    showHistory();
    if (restoreFocus) (dialogContent.querySelector("[data-history-remove]") || dialog.querySelector("[data-dialog-close]")).focus();
  }
  if (!ready) {
    ready = true;
    send("ready");
  }
  if (next.view!==previous.view) fadeIn(get("main"));
  else if (next.rows.length && (!previous.rows.length || next.order!==previous.order)) fadeIn(get("#split"));
});
palette();
send("window");
send("init");
