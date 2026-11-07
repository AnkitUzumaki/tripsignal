const $ = (selector) => document.querySelector(selector);
const form = $("#form");

function localToday() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
}

function formatAge(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value)) return "age unknown";
  if (value < 60) return `${value}s old`;
  if (value < 3600) return `${Math.floor(value / 60)}m old`;
  return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m old`;
}

function safeSourceUrl(value) {
  try {
    const parsed = new URL(value, window.location.origin);
    return parsed.protocol === "https:" ? parsed.href : "#";
  } catch { return "#"; }
}

function setMessage(text, error = false) {
  const message = $("#message");
  message.textContent = text;
  message.className = `message${error ? " error" : ""}`;
}

async function loadAirports() {
  const response = await fetch("/api/airports");
  if (!response.ok) throw new Error("Could not load the airport list.");
  const airports = await response.json();
  for (const select of [$("#origin"), $("#destination")]) {
    for (const [code, airport] of Object.entries(airports).sort(([a], [b]) => a.localeCompare(b))) {
      const option = document.createElement("option");
      option.value = code;
      option.textContent = `${airport.name} (${code})`;
      select.append(option);
    }
  }
  $("#origin").value = "JFK";
  $("#destination").value = "SFO";
}

function render(data) {
  $("#result").classList.remove("hidden");
  const band = $("#band");
  const pill = document.createElement("span");
  pill.className = `pill ${data.score >= 45 ? "high" : data.score >= 20 ? "warn" : data.score === null ? "unknown" : ""}`;
  pill.textContent = data.band;
  band.replaceChildren(pill);
  $("#route").textContent = `${data.route.origin_name} (${data.route.origin}) → ${data.route.destination_name} (${data.route.destination}) · ${data.route.date}`;
  $("#timing").textContent = `Departs ${data.route.departure_local} local · estimated arrival ${data.route.estimated_arrival_local} · ${data.route.estimated_duration_hours} h duration`;
  $("#score").textContent = data.score === null ? "—" : `${data.score}/100`;
  $("#confidence").textContent = `Evidence coverage: ${data.confidence}`;
  $("#action").textContent = data.action;
  $("#reasons").innerHTML = (data.action_reasons || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  $("#checked").textContent = `Checked ${new Date(data.checked_at).toLocaleString()}`;
  $("#evidence-total").textContent = `${data.evidence.length} evidence items`;
  $("#evidence").innerHTML = data.evidence.map(item => {
    const stale = item.stale ? `<span class="pill warn">cached · ${escapeHtml(formatAge(item.cache_age_seconds))}</span>` : "";
    return `<article class="evidence-card"><div class="ev-head"><h4>${escapeHtml(item.title)}</h4><span class="pill ${item.severity === "high" ? "high" : item.severity === "moderate" ? "warn" : item.severity === "unknown" ? "unknown" : ""}">${escapeHtml(item.severity)}</span></div><div class="source">${escapeHtml(item.source)} ${stale}</div><p class="detail">${escapeHtml(item.detail)}</p><div class="ev-meta"><span>Source timestamp: ${escapeHtml(item.observed_at || "not supplied")}</span><a href="${escapeHtml(safeSourceUrl(item.url))}" target="_blank" rel="noopener noreferrer">Open source ↗</a></div></article>`;
  }).join("");
  const coverage = data.coverage || {};
  $("#coverage-summary").textContent = `${coverage.checks_responded ?? "?"}/${coverage.checks_total ?? "?"} checks responded · ${coverage.checks_failed ?? 0} failed`;
  $("#statuses").innerHTML = data.source_status.map(item => `<div class="status-item"><i class="status-dot ${escapeHtml(item.state)}"></i><div><strong>${escapeHtml(item.source)} · ${escapeHtml(item.scope)}</strong><p>${escapeHtml(item.state.replace("_", " "))}: ${escapeHtml(item.message)}</p></div></div>`).join("");
  $("#assumptions").innerHTML = (data.assumptions || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  window.scrollTo({top: $("#result").offsetTop - 18, behavior:"smooth"});
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const button = $("#submit");
  button.disabled = true;
  button.textContent = "Checking public sources…";
  $("#result").classList.add("hidden");
  $("#message").className = "message";
  $("#message").textContent = $("#demo").checked ? "Loading the bundled offline fixture…" : "Checking weather and FAA feeds. This may take a few seconds.";
  try {
    const response = await fetch("/api/assess", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      origin:$("#origin").value,destination:$("#destination").value,date:$("#date").value,
      departure_time:$("#departure").value,duration_hours:Number($("#duration").value),mode:$("#demo").checked ? "demo" : "live"
    })});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Assessment request failed.");
    $("#message").classList.add("hidden");
    render(data);
  } catch (error) {
    setMessage(error.message || "Could not complete the assessment.", true);
  } finally {
    button.disabled = false;
    button.innerHTML = 'Assess trip <span aria-hidden="true">→</span>';
  }
});

const today = localToday();
$("#date").min = today;
$("#date").max = new Date(new Date(`${today}T12:00:00`).getTime() + 7 * 86400000).toISOString().slice(0,10);
$("#date").value = today;
loadAirports().catch(error => setMessage(error.message, true));
