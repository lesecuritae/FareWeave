const $ = (id) => document.getElementById(id);
const state = {
  travelMode: 'ground',
  journeyType: 'round_trip',
  durationNights: 7,
  dticket: (localStorage.getItem('fareweave-dticket') ?? localStorage.getItem('reisevergleich-dticket')) === 'true',
  hotelType: 'hotel',
};

function setTodayDefaults() {
  const now = new Date();
  const departure = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 35);
  const iso = departure.toISOString().slice(0, 10);
  $('departureDate').value = iso;
  $('departureDate').min = new Date().toISOString().slice(0, 10);
  const ret = new Date(departure.getFullYear(), departure.getMonth(), departure.getDate() + 7);
  $('returnDate').value = ret.toISOString().slice(0, 10);
  $('returnDate').min = iso;
}

function dateDifferenceInDays(start, end) {
  if (!start || !end) return null;
  const [sy, sm, sd] = start.split('-').map(Number);
  const [ey, em, ed] = end.split('-').map(Number);
  return Math.round((Date.UTC(ey, em - 1, ed) - Date.UTC(sy, sm - 1, sd)) / 86400000);
}

function syncJourneyDates() {
  const departure = $('departureDate').value;
  const returnDate = $('returnDate').value;
  $('returnDate').min = departure;
  const nights = dateDifferenceInDays(departure, returnDate);
  state.journeyType = returnDate ? 'round_trip' : 'one_way';
  state.durationNights = nights;
  $('oneWayButton').classList.toggle('active', state.journeyType === 'one_way');
  $('oneWayButton').setAttribute('aria-pressed', String(state.journeyType === 'one_way'));
  $('returnDate').setCustomValidity(nights !== null && nights < 0 ? 'Die Rückreise darf nicht vor der Abreise liegen.' : '');
  syncTravelMode();
}

function syncTravelMode() {
  const isGround = state.travelMode === 'ground';
  document.getElementById("lodgingPanel").classList.toggle("hidden", isGround || state.journeyType === 'one_way');
  document.getElementById('ticketPanel').classList.toggle('hidden', state.travelMode === 'flight_stay');
  document.querySelectorAll('.flight-option').forEach(option => {
    option.classList.toggle('hidden', isGround);
  });
  document.querySelectorAll('.feeder-option').forEach(option => {
    option.classList.toggle("hidden", state.travelMode === 'flight_stay' || (isGround && option.classList.contains('flight-option')));
  });
  document.querySelectorAll('[data-dticket]').forEach(button => { button.disabled = state.travelMode === 'flight_stay'; });
  document.getElementById('destinationTransfer').disabled = isGround;
  syncDticket();
}

function syncDticket() {
  document.querySelectorAll('[data-dticket]').forEach(btn => {
    btn.classList.toggle('active', String(state.dticket) === btn.dataset.dticket);
    document.getElementById('dticketOnlyRow').classList.toggle('hidden', !state.dticket || state.travelMode !== 'ground');
    if (!state.dticket) document.getElementById('dticketOnly').checked = false;
  });
}

function syncHotelType() {
  document.querySelectorAll('[data-hotel-type]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.hotelType === state.hotelType);
    btn.setAttribute('aria-checked', String(btn.dataset.hotelType === state.hotelType));
  });
  const hotelUsesStars = state.hotelType === 'hotel' || state.hotelType === 'resort';
  document.getElementById('starsField').classList.toggle('hidden', !hotelUsesStars);
  document.getElementById('lodgingHelp').textContent = state.hotelType === 'hotel'
    ? 'Hotel ist voreingestellt und beginnt bei 3 Sternen. Hostels erscheinen nur im eigenen Hostel-Reiter.'
    : state.hotelType === 'hostel' ? 'Hostels werden ausdrücklich gesucht; eine Hotel-Sterneklasse wird nicht vorausgesetzt.'
    : state.hotelType === 'apartment' ? 'Apartments werden separat gesucht; Hotelsterne werden nicht angewendet.'
    : state.hotelType === 'resort' ? 'Resorts werden mit der gewählten Mindestklassifizierung gesucht.'
    : 'Die Reise wird ohne Unterkunft verglichen.';
}

function showMessage(text, type='') {
  const box = $('message');
  box.textContent = text;
  box.className = `message ${type}`.trim();
}

function hideMessage() { $('message').className = 'message hidden'; }
function money(v, c='EUR') {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return 'Preis offen';
  return new Intl.NumberFormat('de-DE', {style:'currency', currency:c || 'EUR'}).format(Number(v));
}
function hm(value) {
  if (!value) return '–';
  const text = String(value);
  const parsed = new Date(text);
  if (text.includes('T') && !Number.isNaN(parsed.getTime())) {
    return new Intl.DateTimeFormat('de-DE', {hour:'2-digit', minute:'2-digit', hour12:false, timeZone: 'Europe/Berlin'}).format(parsed);
  }
  return text.slice(0, 5);
}
function dateText(value) {
  if (!value) return '–';
  const d = new Date(`${value}T12:00:00`);
  return Number.isNaN(d.getTime()) ? value : new Intl.DateTimeFormat('de-DE', {day:'2-digit', month:'2-digit', year:'numeric'}).format(d);
}
function durationText(mins) {
  if (!mins) return '';
  const h = Math.floor(mins / 60), m = mins % 60;
  return h ? `${h} h ${m ? `${m} min` : ''}`.trim() : `${m} min`;
}
function esc(s='') {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

function getPayload() {
  const originAirports = $('originAirports').value.split(',').map(x => x.trim().toUpperCase()).filter(Boolean);
  const hotelUsesStars = state.hotelType === 'hotel' || state.hotelType === 'resort';
  return {
    journey_type: state.journeyType,
    travel_mode: state.travelMode === 'ground' ? 'ground' : 'flight',
    origin: $('origin').value.trim(),
    destination: $('destination').value.trim(),
    departure_date: $('departureDate').value,
    departure_after: $('departureAfter').value,
    return_mode: 'date',
    duration_value: state.durationNights,
    duration_unit: 'nights',
    return_date: state.journeyType === 'round_trip' ? $('returnDate').value : null,
    deutschlandticket: state.travelMode !== 'flight_stay' && state.dticket,
    include_feeder: state.travelMode === 'flight',
    deutschlandticket_only: state.travelMode === 'ground' && state.dticket && document.getElementById('dticketOnly').checked,
    include_flixtrain: state.travelMode !== 'flight_stay' && $('includeFlixtrain').checked,
    include_flixbus: state.travelMode !== 'flight_stay' && $('includeFlixbus').checked,
    split_ticket_check: state.travelMode !== 'flight_stay' && $('splitTicket').checked,
    include_destination_transfer: state.travelMode !== 'ground' && $('destinationTransfer').checked,
    origin_airports: originAirports,
    destination_airport: $('destinationAirport').value.trim().toUpperCase() || null,
    include_hotel: state.journeyType === 'round_trip' && state.travelMode !== 'ground' && state.hotelType !== 'none',
    hotel_property_type: state.hotelType,
    hotel_min_stars: hotelUsesStars ? Number(document.getElementById('hotelStars').value) : 0,
    airport_buffer_minutes: Number($('airportBuffer').value),
    stops: $('stops').value,
    max_results: 3,
    refresh_cache: $('refreshCache').checked,
  };
}

function actionLinks(offerUrl, manualUrl) {
  if (offerUrl) return `<p class="action-links"><a class="link action-link" href="${esc(offerUrl)}" target="_blank" rel="noreferrer">Angebot prüfen/buchen</a></p>`;
  if (manualUrl) return `<p class="action-links"><a class="link action-link" href="${esc(manualUrl)}" target="_blank" rel="noreferrer">Weitere Angebote öffnen</a></p>`;
  return '';
}

function feederVariantHtml(v) {
  if (!v) return '<p class="muted">Keine passende Variante gefunden.</p>';
  const badges = [];
  if (v.requires_deutschlandticket) badges.push('<span class="badge ticket">Deutschlandticket</span>');
  (v.transport_modes || []).forEach(m => badges.push(`<span class="badge">${esc(m)}</span>`));
  const segs = (v.segments || []).map(seg => {
    const label = seg.line || seg.type || seg.provider || 'Verbindung';
    return `<div class="timeline-row"><div class="time">${hm(seg.departure)} → ${hm(seg.arrival)}</div><div><strong>${esc(label)}</strong><div class="meta">${esc(seg.origin || '')} → ${esc(seg.destination || '')}</div></div><div>${seg.price !== undefined ? money(seg.price, seg.currency) : ''}</div></div>`;
  }).join('');
  return `<div>${badges.join('')}</div><div class="timeline">${segs || `<div class="timeline-row"><div class="time">${hm(v.departure)} → ${hm(v.arrival)}</div><div><strong>${esc(v.label || v.type || 'Verbindung')}</strong><div class="meta">${durationText(v.duration_minutes)}</div></div><div>${money(v.additional_ticket_cost, v.currency)}</div></div>`}</div>${actionLinks(v.offer_url, v.manual_url)}`;
}

function feederCard(title, component) {
  if (!component) return '';
  if (component.manual_required) return `<article class="result-card"><div class="card-head"><div><span class="eyebrow">Zubringer</span><h3>${esc(title)}</h3></div><span class="price-pill">manuell</span></div><p class="muted">Keine automatisch passende Verbindung gefunden.</p></article>`;
  const views = component.views || {};
  const names = [
    ['deutschlandticket','D-Ticket'],
    ['cheapest', views.deutschlandticket ? 'Günstigste Alternative' : 'Günstigste'],
    ['fastest','Schnellste'],
  ].filter(([key]) => views[key]);
  const initial = state.dticket && views.deutschlandticket ? 'deutschlandticket' : (views.cheapest ? 'cheapest' : names[0]?.[0]);
  const tabs = names.map(([key,label]) => `<button type="button" data-view="${key}" class="${key===initial?'active':''}">${label}</button>`).join('');
  const selected = views[initial] || component.selected;
  const price = selected?.price_known ? money(selected.additional_ticket_cost, selected.currency) : 'Preis offen';
  return `<article class="result-card feeder-card" data-feeder='${esc(JSON.stringify(views))}'><div class="card-head"><div><span class="eyebrow">Zubringer</span><h3>${esc(title)}</h3></div><span class="price-pill">${price}</span></div><div class="variant-tabs">${tabs}</div><div class="variant-content">${feederVariantHtml(selected)}</div></article>`;
}

function flightCard(f) {
  if (!f) return '';
  const p = f.price ? money(f.price.value, f.price.currency) : 'Preis offen';
  const o = f.outbound || {}, r = f.return || {};
  return `<article class="result-card"><div class="card-head"><div><span class="eyebrow">Flug</span><h3>${esc(o.from || '')} → ${esc(o.to || '')}</h3></div><span class="price-pill">${p}</span></div><div class="timeline"><div class="timeline-row"><div class="time">${hm(o.departure)} → ${hm(o.arrival)}</div><div><strong>Hinflug</strong><div class="meta">${esc(o.from||'')} → ${esc(o.to||'')} · ${o.stops ?? 0} Stopp(s)</div></div><div></div></div>${r.departure ? `<div class="timeline-row"><div class="time">${hm(r.departure)} → ${hm(r.arrival)}</div><div><strong>Rückflug</strong><div class="meta">${esc(r.from||'')} → ${esc(r.to||'')} · ${r.stops ?? 0} Stopp(s)</div></div><div></div></div>`:''}</div>${actionLinks(f.offer_url, f.manual_url)}</article>`;
}

function transferCard(title, t) {
  if (!t) return '';
  const options = (t.options || []).map(o => `<div class="timeline-row"><div class="time">${hm(o.departure)} → ${hm(o.arrival)}</div><div><strong>${esc(o.type || o.provider || 'Transfer')}</strong><div class="meta">${esc(o.departure_station || '')} → ${esc(o.arrival_station || '')} · ${durationText(o.duration_minutes)}</div></div><div>${o.price !== undefined ? money(o.price,o.currency) : ''}</div></div>`).join('');
  return `<article class="result-card"><div class="card-head"><div><span class="eyebrow">Transfer</span><h3>${esc(title)}</h3></div><span class="price-pill">${t.manual_required?'manuell':'Optionen'}</span></div>${options ? `<div class="timeline">${options}</div>` : '<p class="muted">Keine verifizierte Transferoption gefunden.</p>'}</article>`;
}

function hotelCard(h) {
  if (!h) return '';
  const opts = (h.options || []).slice(0,3);
  const html = opts.map(x => {
    const price = x.price || {};
    const basis = price.basis === 'verified_total_stay' ? 'Gesamtpreis verifiziert' : 'Preis vor Buchung prüfen';
    const classification = x.stars ? `${x.stars} Sterne` : (x.provider_min_stars ? `mindestens ${x.provider_min_stars} Sterne laut Providerfilter` : '');
    const source = x.provider ? ` · Quelle: ${String(x.provider).replace('stay22:', '')} via Stay22` : '';
    return `<div class="hotel"><strong>${esc(x.name || 'Unterkunft')}</strong><div class="muted">${esc(classification)}${x.rating ? ` · ${x.rating}/10` : ''}${esc(source)}</div><div class="hotel-price">${price.value !== undefined ? money(price.value,price.currency) : 'Preis offen'}</div><div class="meta">${esc(basis)}</div>${actionLinks(x.offer_url, null)}</div>`;
  }).join('');
  return `<article class="result-card"><div class="card-head"><div><span class="eyebrow">Unterkunft</span><h3>${dateText(h.checkin)} – ${dateText(h.checkout)}</h3></div></div><div class="hotel-list">${html || '<p class="muted">Keine passende Unterkunft gefunden.</p>'}</div>${actionLinks(null, h.manual_url)}</article>`;
}

function groundAlternativesHtml(title, component) {
  const mixed = (component?.mixed_ticket_options || []).slice(0, 4);
  const split = component?.split_ticket?.status === "success" ? (component.split_ticket.split_options || []).slice(0, 3) : [];
  if (!mixed.length && !split.length) return "";
  const mixedRows = mixed.map(option => {
    const segments = (option.segments || []).map(segment => `<div class="timeline-row"><div class="time">${hm(segment.departure)} → ${hm(segment.arrival)}</div><div><strong>${esc(segment.ticket || segment.provider || segment.line || "Teilstrecke")}</strong><div class="meta">${esc(segment.origin || "")} → ${esc(segment.destination || "")}</div></div><div>${segment.paid_price > 0 ? money(segment.paid_price, segment.currency || "EUR") : ""}</div></div>`).join("");
    return `<section class="alternative"><div class="alternative-head"><div><span class="badge ticket">Mischverbindung</span><strong>${esc(option.label || option.type || "Getrennte Fahrkarten")}</strong></div><b>${option.price_known ? money(option.total_price, option.currency || "EUR") : "Preis offen"}</b></div><div class="timeline">${segments}</div><p class="meta">${esc(option.price_note || "Die Teilpreise gelten für getrennte Fahrkarten.")}</p></section>`;
  }).join("");
  const splitRows = split.map(option => {
    const segments = (option.segments || []).map(segment => `<div class="timeline-row"><div class="time">${hm(segment.departure)} → ${hm(segment.arrival)}</div><div><strong>${esc(segment.origin || "")} → ${esc(segment.destination || "")}</strong><div class="meta">Separates DB-Ticket</div></div><div>${money(segment.price, segment.currency || "EUR")}</div></div>`).join("");
    const station = option.split_station?.name || option.split_station || "Umstieg";
    return `<section class="alternative"><div class="alternative-head"><div><span class="badge">Split-Ticket</span><strong>Trennung in ${esc(station)}</strong></div><b>${money(option.total_price, option.currency || "EUR")}</b></div><div class="timeline">${segments}</div><p class="meta">Ersparnis gegenüber dem geprüften Direktticket: ${money(option.savings, option.currency || "EUR")}</p></section>`;
  }).join("");
  return `<article class="result-card alternatives-card"><div class="card-head"><div><span class="eyebrow">${esc(title)}</span><h3>Misch- & Split-Tickets</h3></div><span class="price-pill">${mixed.length + split.length} Optionen</span></div><div class="alternative-list">${mixedRows}${splitRows}</div></article>`;
}

function reliabilityHtml(connection) {
  const reliability = connection?.reliability;
  if (!reliability) return '';
  if (reliability.status !== 'ok' || reliability.percent === undefined) {
    return `<div class="reliability-summary reliability-empty">Keine ausreichenden historischen Daten</div>`;
  }
  const approximate = reliability.approximate ? 'ca. ' : '';
  const confidence = reliability.approximate ? '<span class="reliability-quality">geringe Datenbasis</span>' : '';
  const legDetails = (connection.legs || []).map(leg => {
    const stats = leg.reliability;
    if (!stats || !stats.sample_count) return '';
    const median = stats.median_arrival_delay_minutes;
    const p90 = stats.p90_arrival_delay_minutes;
    const cancellation = stats.cancellation_rate;
    const quality = stats.quality === 'good' ? 'gut' : stats.quality === 'limited' ? 'begrenzt' : 'gering';
    return `<div class="reliability-leg"><strong>${esc(leg.line || leg.mode || 'Teilstrecke')}</strong><span>${stats.sample_count} historische Fahrten${median !== undefined ? ` · Median ${median >= 0 ? '+' : ''}${esc(median)} min` : ''}${p90 !== undefined ? ` · P90 ${p90 >= 0 ? '+' : ''}${esc(p90)} min` : ''}${cancellation !== undefined ? ` · Ausfälle ${(Number(cancellation) * 100).toFixed(1)} %` : ''} · Datenqualität ${quality}</span></div>`;
  }).join('');
  const connectionDetails = (reliability.connections || []).map(item => item.status === 'ok'
    ? `<div class="reliability-leg"><strong>${esc(item.station || 'Anschluss')}</strong><span>${item.scheduled_transfer_minutes} min Umstieg · ${item.approximate ? 'ca. ' : ''}${item.percent} %</span></div>`
    : '').join('');
  const details = legDetails || connectionDetails ? `<details class="reliability-details"><summary>Historische Details</summary>${connectionDetails}${legDetails}</details>` : '';
  return `<div class="reliability-summary"><strong>${esc(reliability.label)} · ${approximate}${esc(reliability.percent)} %</strong>${confidence}</div>${details}`;
}

function groundConnectionsHtml(title, component) {
  const connections = component?.connections || [];
  if (!connections.length) {
    return `<section class="direction-group" data-direction="${esc(title)}"><div class="direction-heading"><div><span class="eyebrow">Bahn & Bus</span><h2>${esc(title)}</h2></div><span class="muted">0 Verbindungen</span></div><article class="result-card"><p class="muted">Keine automatisch auswertbare Verbindung gefunden.</p></article></section>`;
  }
  const cards = connections.map(connection => {
    const labels = (connection.labels || []).map(label => `<span class="badge ${label === 'D-Ticket' ? 'ticket' : ''}">${esc(label)}</span>`).join('');
    const price = connection.deutschlandticket_covered
      ? '0 € zusätzlich'
      : (connection.price !== undefined ? money(connection.price, connection.currency || 'EUR') : 'Preis offen');
    const legs = (connection.legs || []).map(leg =>
      `<div class="timeline-row connection-leg"><div class="time">${hm(leg.departure)} → ${hm(leg.arrival)}</div><div><strong>${esc(leg.line || leg.mode || 'Teilstrecke')}</strong><div class="meta">${esc(leg.origin || '')} → ${esc(leg.destination || '')}</div></div></div>`
    ).join('');
    const transfers = connection.transfers !== undefined
      ? `${connection.transfers} ${connection.transfers === 1 ? 'Umstieg' : 'Umstiege'}`
      : '';
    return `<article class="result-card connection-card"><div class="card-head"><div><div class="connection-labels">${labels}</div><h3>${hm(connection.departure)} → ${hm(connection.arrival)}</h3><p class="connection-summary">${durationText(connection.duration_minutes)}${transfers ? ` · ${transfers}` : ''}</p>${reliabilityHtml(connection)}</div><span class="price-pill">${price}</span></div><div class="timeline">${legs || '<p class="muted">Keine Teilstrecken verfügbar.</p>'}</div>${actionLinks(connection.offer_url, connection.manual_url)}</article>`;
  }).join('');
  return `<section class="direction-group" data-direction="${esc(title)}"><div class="direction-heading"><div><span class="eyebrow">Bahn & Bus</span><h2>${esc(title)}</h2></div><span class="direction-count">${connections.length} ${connections.length === 1 ? 'Verbindung' : 'Verbindungen'}</span></div><div class="connection-list">${cards}</div></section>`;
}

function render(data) {
  const r = data.response_context || {};
  if (data.status === 'missing_fields') {
    showMessage(data.error || `Fehlende Angaben: ${(data.missing_fields || []).join(', ')}`, 'error');
    $('results').className = 'results hidden';
    return;
  }
  hideMessage();
  const route = r.route || {};
  const cost = r.cost_summary || r.price_summary || {};
  const subtotal = cost.known_subtotal ?? cost.known_total_price ?? cost.round_trip_live_price;
  const complete = cost.complete ?? cost.total_price_complete;
  let html = `<article class="summary-card"><div><h2>${esc(route.origin || $('origin').value)} → ${esc(route.destination || $('destination').value)}</h2><p>${dateText(route.outbound_date)}${route.return_date ? ` bis ${dateText(route.return_date)}` : ''}${route.stay_nights ? ` · ${route.stay_nights} Nächte` : ''}${state.dticket ? ' · Deutschlandticket: Ja' : ' · Deutschlandticket: Nein'}</p></div><div class="total"><strong>${subtotal !== undefined ? money(subtotal, cost.currency || 'EUR') : '–'}</strong><span>${complete ? 'bekannte Gesamtkosten' : 'bekannte Teilsumme'}</span></div></article>`;

  if (data.search_mode === 'ground_trip') {
    const out = r.outbound || {}, back = r.return || {}, dt = r.deutschlandticket || {};
    html += groundConnectionsHtml('Hinfahrt', out);
    html += groundAlternativesHtml('Hinfahrt', out);
    if (r.return) {
      html += groundConnectionsHtml('Rückfahrt', back);
      html += groundAlternativesHtml('Rückfahrt', back);
    }
  } else {
    html += feederCard(`${route.origin || ''} → ${route.origin_airport || 'Flughafen'}`, r.outbound_feeder);
    html += flightCard(r.flight);
    html += transferCard('Flughafen → Ziel', r.outbound_transfer);
    html += hotelCard(r.hotel);
    html += transferCard('Ziel → Flughafen', r.return_transfer);
    html += feederCard(`${route.origin_airport || 'Flughafen'} → ${route.origin || ''}`, r.return_feeder);
  }

  $('results').innerHTML = html;
  $('results').className = 'results';

  document.querySelectorAll('.feeder-card').forEach(card => {
    const views = JSON.parse(card.dataset.feeder || '{}');
    card.querySelectorAll('[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        card.querySelectorAll('[data-view]').forEach(x => x.classList.remove('active'));
        btn.classList.add('active');
        const view = views[btn.dataset.view];
        card.querySelector('.variant-content').innerHTML = feederVariantHtml(view);
        card.querySelector('.price-pill').textContent = view?.price_known ? money(view.additional_ticket_cost, view.currency) : 'Preis offen';
      });
    });
  });
}

async function submit(ev) {
  ev.preventDefault();
  hideMessage();
  $('results').className = 'results hidden';
  const btn = $('searchButton');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Suche läuft';
  $('statusBadge').textContent = 'Suche läuft';
  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(getPayload()),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ? JSON.stringify(data.detail) : `HTTP ${res.status}`);
    render(data);
    $('statusBadge').textContent = data.cache?.journey_hit ? 'Cache' : 'Live';
  } catch (err) {
    showMessage(`Suche fehlgeschlagen: ${err.message}`, 'error');
    $('statusBadge').textContent = 'Fehler';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Verbindungen finden';
  }
}

function bind() {
  setTodayDefaults();
  syncJourneyDates();
  syncHotelType();
  document.querySelectorAll('[data-mode]').forEach(btn => btn.addEventListener('click', () => {
    state.travelMode = btn.dataset.mode;
    document.querySelectorAll('[data-mode]').forEach(x => x.classList.toggle('active', x===btn));
    syncTravelMode();
  }));
  document.querySelectorAll('[data-dticket]').forEach(btn => btn.addEventListener('click', () => {
    state.dticket = btn.dataset.dticket === 'true';
    localStorage.setItem('fareweave-dticket', String(state.dticket));
    syncDticket();
  }));
  document.querySelectorAll("[data-hotel-type]").forEach(btn => btn.addEventListener("click", () => {
    if (state.travelMode === "ground") return;
    state.hotelType = btn.dataset.hotelType;
    syncHotelType();
  }));
  $('departureDate').addEventListener('change', syncJourneyDates);
  $('returnDate').addEventListener('change', syncJourneyDates);
  $('oneWayButton').addEventListener('click', () => {
    $('returnDate').value = '';
    syncJourneyDates();
  });
  $('searchForm').addEventListener('submit', submit);
}

document.addEventListener('DOMContentLoaded', bind);
