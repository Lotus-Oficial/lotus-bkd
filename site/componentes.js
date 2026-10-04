// Lótus · página de componentes: totais por casa, abas, filtros e lista agrupada por etapa.
// Os dados vêm de dados-componentes.js (window.LOTUS_COMPONENTES e window.LOTUS_ETAPAS).

const ITENS = window.LOTUS_COMPONENTES;
const ETAPAS = window.LOTUS_ETAPAS;
const SITES = { esp: "Site ESP", clp: "Site CLP" };
const STATUS = { comprar: "a comprar", comprado: "comprado", tenho: "já tenho" };

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const brl0 = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const $ = (s) => document.querySelector(s);

let site = location.hash === "#clp" ? "clp" : "esp";
let filtro = "todos";

// valor unitário que vale para o item: pago, se houver, senão a estimativa
const unit = (i) => i.pago ?? i.estimativa ?? 0;

function resumo(itens) {
  const custo = itens.filter((i) => i.status !== "tenho");
  return {
    previsto: custo.reduce((s, i) => s + unit(i) * i.qtd, 0),
    gasto: custo.filter((i) => i.status === "comprado").reduce((s, i) => s + (i.pago ?? 0) * i.qtd, 0),
    falta: custo.filter((i) => i.status === "comprar").reduce((s, i) => s + (i.estimativa ?? 0) * i.qtd, 0),
    reaproveitado: itens.filter((i) => i.status === "tenho").reduce((s, i) => s + (i.estimativa ?? 0) * i.qtd, 0),
    total: custo.length,
    comprados: custo.filter((i) => i.status === "comprado").length,
  };
}

function cardTotal(titulo, r, extra = "") {
  const pct = r.total ? Math.round((r.comprados / r.total) * 100) : 0;
  return `
    <article class="total ${extra}">
      <span class="total-kicker">${titulo}</span>
      <strong class="total-value">${brl0.format(r.previsto)}</strong>
      <span class="total-sub">previsto</span>
      <div class="meter" style="--w:${pct}%"><span></span></div>
      <dl class="total-split">
        <div><dt>gasto</dt><dd class="ok">${brl0.format(r.gasto)}</dd></div>
        <div><dt>falta</dt><dd>${brl0.format(r.falta)}</dd></div>
        <div><dt>itens</dt><dd>${r.comprados}/${r.total}</dd></div>
      </dl>
      ${r.reaproveitado ? `<p class="total-reuse"><span>+ ${brl0.format(r.reaproveitado)}</span> em equipamento reaproveitado · valor total ${brl0.format(r.previsto + r.reaproveitado)}</p>` : ""}
    </article>`;
}

function renderTotais() {
  $("#totals").innerHTML =
    cardTotal("Site ESP", resumo(ITENS.filter((i) => i.site === "esp"))) +
    cardTotal("Site CLP", resumo(ITENS.filter((i) => i.site === "clp"))) +
    cardTotal("Projeto inteiro", resumo(ITENS), "total-all");
}

function linkLoja(i) {
  if (i.loja && i.status === "tenho")
    return `<a class="lnk" href="${i.loja}" target="_blank" rel="noopener" title="Anúncio usado como valor de referência">Referência ↗</a>`;
  if (i.loja) return `<a class="lnk lnk-shop" href="${i.loja}" target="_blank" rel="noopener">Loja ↗</a>`;
  if (i.busca)
    return `<a class="lnk" href="https://lista.mercadolivre.com.br/${encodeURIComponent(i.busca.replace(/\s+/g, "-"))}" target="_blank" rel="noopener">Buscar ↗</a>`;
  return "";
}

function linkManual(i) {
  return i.manual
    ? `<a class="lnk lnk-doc" href="${i.manual}" target="_blank" rel="noopener">Manual</a>`
    : `<span class="lnk lnk-off" title="Manual ainda não salvo">Manual</span>`;
}

function preco(i) {
  if (i.status === "tenho")
    return i.estimativa != null
      ? `<span class="price-ref" title="Valor de referência de mercado">ref. ${brl.format(i.estimativa)}</span>`
      : `<span class="price-muted">reaproveitado</span>`;
  if (i.pago != null) return `<span class="price-paid">${brl.format(i.pago)}</span>`;
  if (i.estimativa != null) return `<span class="price-est">~${brl.format(i.estimativa)}</span>`;
  return `<span class="price-muted">—</span>`;
}

function linha(i) {
  const sub = i.status === "tenho" ? "—" : brl.format(unit(i) * i.qtd);
  const un = i.unidade ?? "un";
  return `
    <li class="item is-${i.status}">
      <span class="pill pill-${i.status}">${STATUS[i.status]}</span>
      <div class="item-main">
        <strong>${i.nome}</strong>
        <span>${i.spec}</span>
      </div>
      <span class="item-qtd">${i.qtd} <small>${un}</small></span>
      <span class="item-price">${preco(i)}</span>
      <span class="item-sub ${i.pago != null ? "is-paid" : ""}">${sub}</span>
      <span class="item-links">${linkLoja(i)}${linkManual(i)}</span>
    </li>`;
}

function renderGrupos() {
  const doSite = ITENS.filter((i) => i.site === site);
  const html = Object.entries(ETAPAS)
    .map(([key, et]) => {
      const todos = doSite.filter((i) => i.etapa === key);
      const itens = todos.filter((i) => filtro === "todos" || i.status === filtro);
      if (!itens.length) return "";
      const r = resumo(todos);
      const agora = site === "esp" && key === "bancada";
      return `
        <section class="group ${agora ? "is-now" : ""}">
          <header class="group-head">
            <div>
              <h2>${et.nome} ${agora ? '<span class="badge">comece por aqui</span>' : ""}</h2>
              <p>${et.desc}</p>
            </div>
            <div class="group-total">
              <strong>${brl0.format(r.previsto)}</strong>
              <span>${r.comprados}/${r.total} comprados</span>
            </div>
          </header>
          <div class="cols" aria-hidden="true">
            <span>status</span><span>item</span><span>qtd</span><span>unitário</span><span>subtotal</span><span></span>
          </div>
          <ul class="items">${itens.map(linha).join("")}</ul>
        </section>`;
    })
    .join("");
  $("#groups").innerHTML = html || `<p class="empty">Nenhum item com esse filtro em ${SITES[site]}.</p>`;
}

function liga(sel, attr, set) {
  document.querySelectorAll(sel).forEach((b) =>
    b.addEventListener("click", () => {
      document.querySelectorAll(sel).forEach((x) => x.classList.toggle("is-active", x === b));
      set(b.dataset[attr]);
      renderGrupos();
    })
  );
}

liga("#siteTabs .tab", "site", (v) => (site = v));
liga("#filters .filter", "status", (v) => (filtro = v));
document.querySelectorAll("#siteTabs .tab").forEach((t) => t.classList.toggle("is-active", t.dataset.site === site));
renderTotais();
renderGrupos();
