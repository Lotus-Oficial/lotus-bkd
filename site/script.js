// Lótus · interações da página de apresentação.
// Sem dependências: simula um ciclo de rega, desenha gotas no fundo e revela seções ao rolar.

const SITES = {
  esp: {
    hw: "ESP32 · ESPHome sprinkler · 7 zonas",
    zones: [
      ["Gramado frente", "aspersor", 8],
      ["Canteiro muro", "gotejamento", 6],
      ["Horta", "gotejamento · 16mm", 10],
      ["Frutíferas", "gotejamento", 12],
      ["Vasos varanda", "microaspersor", 4],
      ["Gramado fundo", "aspersor", 8],
      ["Cerca viva", "gotejamento", 6],
    ],
    sensors: [
      ["Chuva", "seco", "sun"],
      ["Bomba", "ligada", "ok"],
      ["Boia", "nível ok", "ok"],
      ["Próximo", "06:00", ""],
    ],
  },
  clp: {
    hw: "CLP Delta DVP20SX2 · inversor IF10 · 5 zonas",
    zones: [
      ["Pomar", "gotejamento", 14],
      ["Jardim entrada", "aspersor", 8],
      ["Horta", "gotejamento · 16mm", 10],
      ["Gramado", "aspersor", 10],
      ["Floreiras", "microaspersor", 5],
    ],
    sensors: [
      ["Pressão", "2,4 bar", "water"],
      ["Vazão", "18 L/min", "water"],
      ["Inversor", "52 Hz · PID", "ok"],
      ["Modo", "automático", "ok"],
    ],
  },
};

const SPEED = 30; // segundos simulados por segundo real
const $ = (s) => document.querySelector(s);

let site = "esp";
let zone = 2;
let remaining = 0;

const fmt = (s) => {
  s = Math.max(0, Math.round(s));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};

function render() {
  const data = SITES[site];
  const [name, kind, min] = data.zones[zone];
  const total = min * 60;

  $("#hw").textContent = data.hw;
  $("#zoneName").textContent = `Zona ${zone + 1} · ${name}`;
  $("#zoneSub").textContent = kind;
  $("#time").textContent = fmt(remaining);
  $("#ring").style.setProperty("--p", ((1 - remaining / total) * 100).toFixed(1));

  $("#zones").innerHTML = data.zones
    .map(([n, , m], i) => {
      const state = i < zone ? "is-done" : i === zone ? "is-active" : "";
      const ico = i < zone ? "✓" : i + 1;
      const meta = i < zone ? "feito" : i === zone ? fmt(remaining) : `${m} min`;
      return `<li class="zone ${state}"><span class="z-ico">${ico}</span><span>${n}</span><span class="z-meta">${meta}</span></li>`;
    })
    .join("");

  $("#sensors").innerHTML = data.sensors
    .map(([k, v, c]) => `<div class="sensor"><span>${k}</span><b class="${c}">${v}</b></div>`)
    .join("");
}

function startZone(i) {
  const zones = SITES[site].zones;
  zone = i % zones.length;
  remaining = zones[zone][2] * 60 * 0.62;
  render();
}

document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("is-active", t === tab));
    site = tab.dataset.site;
    startZone(2);
  })
);

startZone(2);
setInterval(() => {
  remaining -= SPEED;
  if (remaining <= 0) {
    const zones = SITES[site].zones;
    zone = (zone + 1) % zones.length;
    remaining = zones[zone][2] * 60;
  }
  render();
}, 1000);

// ---- Gotas caindo no fundo ----
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const canvas = $("#rain");
const ctx = canvas.getContext("2d");
let drops = [];

function resize() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = innerWidth * dpr;
  canvas.height = innerHeight * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const count = Math.round(innerWidth / 26);
  drops = Array.from({ length: count }, () => newDrop(true));
}

function newDrop(anywhere) {
  return {
    x: Math.random() * innerWidth,
    y: anywhere ? Math.random() * innerHeight : -20,
    len: 8 + Math.random() * 18,
    speed: 0.6 + Math.random() * 1.6,
    alpha: 0.05 + Math.random() * 0.16,
  };
}

function frame() {
  ctx.clearRect(0, 0, innerWidth, innerHeight);
  for (const d of drops) {
    const g = ctx.createLinearGradient(d.x, d.y, d.x, d.y + d.len);
    g.addColorStop(0, "rgba(127,215,234,0)");
    g.addColorStop(1, `rgba(127,215,234,${d.alpha})`);
    ctx.strokeStyle = g;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(d.x, d.y);
    ctx.lineTo(d.x, d.y + d.len);
    ctx.stroke();
    d.y += d.speed;
    if (d.y > innerHeight) Object.assign(d, newDrop(false));
  }
  requestAnimationFrame(frame);
}

if (!reduced) {
  resize();
  addEventListener("resize", resize);
  requestAnimationFrame(frame);
}

// ---- Revelar seções ao rolar ----
const io = new IntersectionObserver(
  (entries) =>
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      }
    }),
  { threshold: 0.15 }
);
document.querySelectorAll(".reveal").forEach((el, i) => {
  el.style.transitionDelay = `${(i % 4) * 80}ms`;
  io.observe(el);
});
