// Version-aware RAG demo: browser-side retrieval over the B1 Kafka corpus.
// Chunk vectors come from the Python pipeline (Chroma); questions are embedded here with
// transformers.js using the same model at fp32, which reproduces the Python top-4 exactly.
import { pipeline } from "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

const site = await (await fetch("data/b1.json")).json();
const K = site.k;
let embedder = null;

const EXAMPLES = ["kafka-001", "kafka-007", "kafka-009", "kafka-005", "kafka-017", "kafka-020"];

function setStatus(text) { $("status").textContent = text; }

async function loadModel() {
  if (embedder) return embedder;
  $("bar").style.display = "block";
  const seen = {};
  embedder = await pipeline("feature-extraction", site.model, {
    dtype: "fp32",
    progress_callback: (p) => {
      if (p.status === "progress" && p.total) {
        seen[p.file] = [p.loaded, p.total];
        const [l, t] = Object.values(seen).reduce((a, [x, y]) => [a[0] + x, a[1] + y], [0, 0]);
        $("barfill").style.width = `${Math.round((100 * l) / t)}%`;
        setStatus(`Downloading the model (once): ${(l / 1e6).toFixed(0)} of ${(t / 1e6).toFixed(0)} MB…`);
      }
    },
  });
  $("bar").style.display = "none";
  return embedder;
}

const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };

function search(qv, versionAware) {
  const pool = versionAware ? site.chunks.filter((c) => !c.superseded) : site.chunks;
  return pool.map((c) => ({ c, sim: dot(qv, c.vec) })).sort((a, b) => b.sim - a.sim).slice(0, K);
}

function renderHits(target, verdictEl, hits) {
  target.replaceChildren();
  const stale = hits.filter((h) => h.c.superseded).length;
  verdictEl.replaceChildren();
  const b = el("b", stale ? "bad" : "good", stale ? `${stale} of ${hits.length} superseded` : "0 superseded");
  verdictEl.append(b, document.createTextNode(stale
    ? ": outdated runbooks would reach the LLM"
    : ": only current runbooks reach the LLM"));
  hits.forEach((h, i) => {
    const box = el("div", "hit" + (h.c.superseded ? " sup" : ""));
    const top = el("div", "top");
    top.append(el("span", "rank", `#${i + 1}`), el("span", "file", h.c.file),
      el("span", "badge " + (h.c.superseded ? "old" : "cur"),
        `${h.c.superseded ? "SUPERSEDED" : "current"} · v${h.c.version} · ${h.c.effective_date}`),
      el("span", "sim", `similarity ${h.sim.toFixed(3)}`));
    const det = el("details");
    det.append(el("summary", null, "show chunk text"), el("pre", "chunk", h.c.text));
    box.append(top, det);
    target.append(box);
  });
}

async function run(question) {
  question = question.trim();
  if (!question) return;
  $("go").disabled = true;
  try {
    if (!embedder) setStatus("Loading the model…");
    const model = await loadModel();
    setStatus("Embedding your question…");
    const t0 = performance.now();
    const qv = Array.from((await model(question, { pooling: "mean", normalize: true })).data);
    const off = search(qv, false), on = search(qv, true);
    renderHits($("off"), $("voff"), off);
    renderHits($("on"), $("von"), on);
    setStatus(`Searched 17 chunks twice in ${(performance.now() - t0).toFixed(0)} ms, entirely in your browser.`);
  } catch (e) {
    setStatus(`Could not load the model (${e.message}). Check your connection and try again.`);
  } finally {
    $("go").disabled = false;
  }
}

$("askform").addEventListener("submit", (ev) => { ev.preventDefault(); run($("q").value); });

const byId = Object.fromEntries(site.cases.map((c) => [c.id, c]));
for (const id of EXAMPLES) {
  const c = byId[id];
  const chip = el("button", "chip", c.question.length > 58 ? c.question.slice(0, 56) + "…" : c.question);
  chip.type = "button";
  chip.title = c.question;
  chip.addEventListener("click", () => { $("q").value = c.question; run(c.question); });
  $("chips").append(chip);
}

const word = (p) => (p === null ? "—" : p ? "PASS" : "FAIL");
const supCount = (files) => files.filter((f) => site.chunks.find((c) => c.file === f)?.superseded).length;
for (const c of site.cases) {
  const tr = el("tr");
  const q = el("button", "qlink", c.question);
  q.type = "button";
  q.addEventListener("click", () => { $("q").value = c.question; window.scrollTo({ top: 0, behavior: "smooth" }); run(c.question); });
  const tdq = el("td"); tdq.append(q);
  const cls = (p) => (p === null ? "" : p ? "p" : "f");
  tr.append(el("td", null, c.id), el("td", null, c.type), tdq,
    el("td", cls(c.off.pass), word(c.off.pass)), el("td", cls(c.on.pass), word(c.on.pass)),
    el("td", null, `${supCount(c.off.files)} → ${supCount(c.on.files)}`));
  $("cases").append(tr);
}

const pairs = {};
for (const ch of site.chunks) {
  const p = (pairs[ch.doc_title] ||= {});
  p[ch.superseded ? "old" : "cur"] = ch;
}
for (const [title, p] of Object.entries(pairs)) {
  const conf = (site.conflicts[title] || []).find((x) => !["owner"].includes(x.field)) || {};
  const tr = el("tr");
  tr.append(el("td", null, title),
    el("td", null, `${p.cur.file} (v${p.cur.version}, ${p.cur.effective_date})`),
    el("td", null, `${p.old.file} (v${p.old.version}, ${p.old.effective_date})`),
    el("td", null, conf.old ? `${conf.field}: ${conf.old} → ${conf.current}` : ""));
  $("corpus").append(tr);
}
