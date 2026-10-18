// B1 Track B flow deck — structured pptxgenjs build (theme, layouts, sections, notes).
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.SKILL + "/scripts/apply_theme.js");
const OUT = process.argv[2];

const THEME = {
  name: "B1 Kafka Versioning",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1F2A37", lt1: "FFFFFF", dk2: "0B6E61", lt2: "EEF2F5",
    accent1: "0F9D8A",  // current version / done
    accent2: "E8833A",  // superseded / the new stage / next
    accent3: "B42318",  // fail
    accent4: "64748B",  // neutral grey
    accent5: "CDEFEA",  // light teal tint
    accent6: "FDEBDC",  // light amber tint
    hlink: "0F9D8A", folHlink: "0B6E61",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "B1 Version-Aware Retrieval — Track B flow";
pres.author = "Shreenath Shetty";
pres.subject = "Modern AI Pro Level 2, Track B, project B1";
const C = pres.SchemeColor;
const W = 13.333, M = 0.6;

// ── layouts ──────────────────────────────────────────────────────────────────
pres.defineSlideMaster({
  title: "Title Dark",
  background: { color: HEX.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 1.95, w: 12.1, h: 1.95,
        fontSize: 44, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.1, w: 11.5, h: 1.2,
        fontSize: 20, color: C.accent5, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Content",
  background: { color: HEX.lt1 },
  margin: [0.5, 0.6, 0.7, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: 12.1, h: 0.95,
        fontSize: 34, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "B1 Version-Aware Retrieval · Track B · Kafka runbooks",
        options: { x: M, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: C.accent4, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.55, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});

// ── helpers ──────────────────────────────────────────────────────────────────
const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontFace: undefined, ...o });
const shadow = () => ({ type: "outer", color: "000000", opacity: 0.12, blur: 6, offset: 2, angle: 90 });
function card(s, x, y, w, h, fill, name, line) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, objectName: name,
    fill: { color: fill }, line: line ? { color: line, width: 1.5 } : { type: "none" }, shadow: shadow() });
}
function circle(s, x, y, d, fill, label, txt, name) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: name });
  T(s, label, { x, y, w: d, h: d, align: "center", valign: "middle", bold: true, fontSize: d > 0.6 ? 18 : 14, color: txt });
}
function arrow(s, x1, y1, x2, y2, name) {
  s.addShape(pres.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, objectName: name,
    line: { color: HEX.accent4, width: 1.75, endArrowType: "triangle" } });
}
const content = (section, title) => {
  const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
  s.addText(title, { placeholder: "title", bold: true, align: "left" });
  return s;
};

// ── 1. title ─────────────────────────────────────────────────────────────────
pres.addSection({ title: "Overview" });
let s = pres.addSlide({ masterName: "Title Dark", sectionTitle: "Overview" });
s.addText("B1 Version-Aware Retrieval", { placeholder: "title", bold: true, align: "left" });
s.addText("Track B · Kafka runbooks · how the flow works, step by step", { placeholder: "body" });
T(s, "Modern AI Pro · Level 2 · RAG Design   |   Shreenath Shetty   |   v7 · 2026-10-18",
  { x: M, y: 6.6, w: 12, h: 0.35, fontSize: 12, color: C.accent4 });
circle(s, M, 1.0, 0.7, HEX.accent2, "B1", HEX.lt1, "badge");
s.addNotes("This deck walks through Track B of project B1: making a RAG system stop answering from outdated runbooks. Steps 2 to 5 are done; Step 6, freezing the test set, is next.");

// ── 2. the problem ───────────────────────────────────────────────────────────
s = content("Overview", "Old runbooks win on similarity alone");
card(s, M, 1.55, 3.9, 2.55, HEX.accent6, "old card");
T(s, "disk-capacity-2025.md", { x: M + 0.3, y: 1.75, w: 3.4, h: 0.35, fontSize: 14, bold: true, color: C.text1 });
T(s, "Version 2 · 2025-02-01", { x: M + 0.3, y: 2.1, w: 3.4, h: 0.3, fontSize: 12, color: C.accent4 });
T(s, "Page at 90% used", { x: M + 0.3, y: 2.6, w: 3.4, h: 0.6, fontSize: 26, bold: true, color: C.accent2 });
T(s, "Reads like a live document. Nothing says it is outdated.", { x: M + 0.3, y: 3.25, w: 3.4, h: 0.7, fontSize: 13, color: C.text1 });

card(s, M, 4.35, 3.9, 2.4, HEX.accent5, "current card");
T(s, "disk-capacity.md", { x: M + 0.3, y: 4.55, w: 3.4, h: 0.35, fontSize: 14, bold: true, color: C.text1 });
T(s, "Version 3 · 2026-05-01", { x: M + 0.3, y: 4.9, w: 3.4, h: 0.3, fontSize: 12, color: C.accent4 });
T(s, "Page at 85% used", { x: M + 0.3, y: 5.4, w: 3.4, h: 0.6, fontSize: 26, bold: true, color: C.accent1 });
T(s, "Same wording, different facts.", { x: M + 0.3, y: 6.05, w: 3.4, h: 0.4, fontSize: 13, color: C.text1 });

const stats = [
  ["0.87–0.97", "similarity between old and current versions of the same runbook"],
  ["4 / 8", "plain questions where the OLD version ranks first"],
  ["8 / 8", "questions where both versions land in the top 2, so both reach the LLM"],
];
stats.forEach(([n, l], i) => {
  const y = 1.6 + i * 1.75;
  T(s, n, { x: 5.2, y, w: 3.4, h: 1.0, fontSize: 48, bold: true, color: i === 1 ? C.accent2 : C.text1, fontFace: THEME.headFontFace });
  T(s, l, { x: 8.75, y: y + 0.12, w: 3.95, h: 0.8, fontSize: 15, color: C.text1, valign: "middle" });
});
s.addNotes("Old and new runbooks are near-duplicates. Embedding search measures meaning, not validity, so it cannot tell which one is current. Measured with the lab's own embedder: in 4 of 8 plain questions the old version ranks first, and in every case both are in the top 2. With top-4 retrieval, roughly half the context the LLM sees is stale.");

// ── 3. the fix: flow ─────────────────────────────────────────────────────────
s = content("Overview", "B1 adds one stage: a version filter");
function lane(y, label, sub, boxes) {
  T(s, label, { x: M, y: y + 0.12, w: 1.3, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
  T(s, sub, { x: M, y: y + 0.5, w: 1.3, h: 0.35, fontSize: 11, color: C.accent4 });
  let x = 2.05; const gap = 0.32;
  boxes.forEach(([t, st, kind, w], i) => {
    const fill = kind === "new" ? HEX.accent6 : kind === "meta" ? HEX.accent5 : HEX.lt2;
    const line = kind === "new" ? HEX.accent2 : kind === "meta" ? HEX.accent1 : null;
    card(s, x, y, w, 1.05, fill, `${label} ${t}`, line);
    T(s, t, { x: x + 0.08, y: y + 0.12, w: w - 0.16, h: 0.45, fontSize: 15, bold: true, align: "center",
      color: kind === "new" ? C.accent2 : C.text1 });
    T(s, st, { x: x + 0.08, y: y + 0.55, w: w - 0.16, h: 0.4, fontSize: 11, align: "center", color: C.accent4 });
    if (i < boxes.length - 1) arrow(s, x + w + 0.03, y + 0.52, x + w + gap - 0.03, y + 0.52, `${label} arrow ${i}`);
    x += w + gap;
  });
}
lane(1.75, "INGEST", "rag.py ingest", [
  ["16 runbooks", "corpus/kafka/", "src", 1.55], ["load", "read files", "src", 1.25],
  ["+ metadata", "manifest.json · Step 8", "meta", 1.95], ["chunk", "split text", "src", 1.25],
  ["embed", "MiniLM-L6-v2", "src", 1.55], ["Chroma", "vectors + metadata", "src", 1.6]]);
lane(3.65, "QUERY", "ask / b1_eval", [
  ["question", "from the user", "src", 1.55], ["embed", "same model", "src", 1.25],
  ["VERSION FILTER", "superseded = False", "new", 2.25], ["top-4", "by similarity", "src", 1.55],
  ["LLM answer", "with citations", "src", 2.15]]);
const legend = [["accent6", HEX.accent2, "New stage, switchable OFF / ON"],
  ["accent5", HEX.accent1, "The metadata it needs (Steps 4 and 8)"], ["lt2", null, "Unchanged lab code"]];
legend.forEach(([f, l, t], i) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.05 + i * 3.9, y: 5.45, w: 0.35, h: 0.3, rectRadius: 0.05,
    fill: { color: HEX[f] }, line: l ? { color: l, width: 1.25 } : { type: "none" }, objectName: `legend ${i}` });
  T(s, t, { x: 2.5 + i * 3.9, y: 5.4, w: i === 0 ? 3.4 : 3.3, h: 0.4, fontSize: 12, color: C.text1, valign: "middle" });
});
T(s, "Old chunks are removed before ranking. They never compete, so they can't win.",
  { x: 2.05, y: 6.1, w: 10.5, h: 0.45, fontSize: 16, italic: true, color: C.text2 });
s.addNotes("Every box except VERSION FILTER already exists in simple_rag/rag.py. At ingest, each chunk gets the manifest fields. At query time, Chroma's where clause drops superseded chunks before similarity ranking. This is structural, not a prompt instruction like 'prefer the newest document'.");

// ── 4. roadmap ───────────────────────────────────────────────────────────────
pres.addSection({ title: "Progress" });
s = content("Progress", "All twelve steps done");
const steps = [
  [1, "Team setup", "na"], [2, "Run lab unchanged", "done"], [3, "Versioned corpus", "done"],
  [4, "Metadata manifest", "done"], [5, "Golden set", "done"], [6, "Freeze in Git", "done"],
  [7, "BEFORE run", "done"], [8, "Metadata to Chroma", "done"], [9, "Query filter", "done"],
  [10, "OFF / ON switch", "done"], [11, "AFTER run", "done"], [12, "Results table", "done"]];
steps.forEach(([n, t, st], i) => {
  const row = Math.floor(i / 6), col = i % 6;
  const x = M + 0.25 + col * 2.05, y = 1.75 + row * 2.35;
  const fill = st === "done" ? HEX.accent1 : st === "next" ? HEX.accent2 : st === "na" ? HEX.lt2 : HEX.lt1;
  if (st === "todo") s.addShape(pres.shapes.OVAL, { x, y, w: 0.85, h: 0.85, fill: { color: HEX.lt1 },
    line: { color: HEX.accent4, width: 1.5 }, objectName: `step ${n}` });
  else s.addShape(pres.shapes.OVAL, { x, y, w: 0.85, h: 0.85, fill: { color: fill }, line: { type: "none" }, objectName: `step ${n}` });
  T(s, String(n), { x, y, w: 0.85, h: 0.85, align: "center", valign: "middle", fontSize: 20, bold: true,
    color: st === "done" || st === "next" ? C.background1 : C.text1 });
  T(s, t, { x: x - 0.4, y: y + 0.95, w: 1.65, h: 0.5, fontSize: 13, align: "center", color: C.text1 });
  T(s, st === "done" ? "Done" : st === "next" ? "Next" : st === "na" ? "N/A" : "", {
    x: x - 0.4, y: y + 1.38, w: 1.65, h: 0.3, fontSize: 11, align: "center", bold: true,
    color: st === "done" ? C.accent1 : st === "next" ? C.accent2 : C.accent4 });
  if (col < 5) arrow(s, x + 0.95, y + 0.425, x + 1.95, y + 0.425, `road arrow ${n}`);
});
T(s, "Data first (Steps 3–6), committed before any code change. Then measure BEFORE, add the filter, measure AFTER.",
  { x: M, y: 6.35, w: 12.1, h: 0.45, fontSize: 14, color: C.text2, italic: true });
s.addNotes("Teal is done, orange is next, outlined is still to do. Step 1 is not applicable because this is an individual project. Step 6 froze the 21 cases in commit 2cff45a. The order matters: the corpus and test cases are committed before rag.py changes, so the test can't be shaped by the fix.");

// ── 5. where things live ─────────────────────────────────────────────────────
s = content("Progress", "Two folders: the code and the evidence");
function folder(x, title, sub, rows, tint, line) {
  card(s, x, 1.6, 5.9, 5.1, tint, title, line);
  T(s, title, { x: x + 0.3, y: 1.8, w: 5.3, h: 0.45, fontSize: 20, bold: true, color: C.text1, fontFace: THEME.headFontFace });
  T(s, sub, { x: x + 0.3, y: 2.25, w: 5.3, h: 0.35, fontSize: 12, color: C.accent4 });
  rows.forEach(([f, d], i) => {
    T(s, f, { x: x + 0.3, y: 2.8 + i * 0.6, w: 2.45, h: 0.5, fontSize: 13, bold: true, color: C.text1, fontFace: "Courier New", valign: "middle" });
    T(s, d, { x: x + 2.85, y: 2.8 + i * 0.6, w: 2.85, h: 0.5, fontSize: 13, color: C.text1, valign: "middle" });
  });
}
folder(M, "track-b-kafka/simple_rag/", "Git repo · branch track-b · the code", [
  ["corpus/kafka/", "16 runbooks + manifest.json"], ["golden_kafka.jsonl", "21 test cases"],
  ["b1_check.py", "data tests, Steps 3–5"], ["rag.py", "pipeline; changes in 7–10"],
  ["b1_eval.py", "OFF/ON evaluator (Step 7)"], ["results/", "BEFORE, AFTER, summary"]], HEX.lt2, null);
folder(6.83, "b1-tracking/track-b/", "Evidence and documentation", [
  ["SOP.md", "the runbook (source)"], ["docs/", "this deck + SOP PDF"],
  ["runs/step02…05/", "log of every run"], ["tools/", "make_corpus.py generator"]], HEX.accent5, HEX.accent1);
s.addNotes("The repo holds what gets graded. The tracking folder holds how it was built and tested: logs from every run, the SOP, and the generator that recreates the corpus byte for byte.");

// ── 6. step 2 ────────────────────────────────────────────────────────────────
pres.addSection({ title: "Steps 2–12" });
s = content("Steps 2–12", "Step 2: the unchanged lab runs end to end");
const s2 = [["ingest", "196", "vectors stored from the Aventro corpus"],
  ["ask", "21 s", "cited answer through the class proxy"], ["eval", "2 / 6", "retrieval and answer: the lab's designed start"]];
s2.forEach(([c, n, l], i) => {
  const x = M + i * 4.1;
  card(s, x, 1.8, 3.8, 3.3, HEX.lt2, `step2 ${c}`);
  T(s, `rag.py ${c}`, { x: x + 0.3, y: 2.0, w: 3.2, h: 0.4, fontSize: 15, bold: true, color: C.text2, fontFace: "Courier New" });
  T(s, n, { x: x + 0.3, y: 2.55, w: 3.2, h: 1.1, fontSize: 54, bold: true, color: C.text1, fontFace: THEME.headFontFace });
  T(s, l, { x: x + 0.3, y: 3.8, w: 3.2, h: 0.9, fontSize: 15, color: C.text1 });
});
T(s, "Why: if something breaks later, you know it worked before you touched it.",
  { x: M, y: 5.6, w: 12.1, h: 0.45, fontSize: 16, italic: true, color: C.text2 });
T(s, "Evidence: runs/step02-baseline-unchanged/", { x: M, y: 6.15, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("Guide step 2: run the lab exactly as shipped before changing anything. All three commands worked. The 2 out of 6 eval score is the lab's built-in starting point, not a fault introduced here.");

// ── 7. step 3 ────────────────────────────────────────────────────────────────
s = content("Steps 2–12", "Step 3: eight subjects, two versions each");
const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk1 }, fontSize: 13 } });
const rows3 = [
  ["Consumer lag", "page at 100,000 messages", "page at 10 min of time lag"],
  ["Topic retention", "7 days (604800000 ms)", "3 days (259200000 ms)"],
  ["Rolling restart", "wait 5 min between brokers", "wait 10 min, controller last"],
  ["Listeners and auth", "9092 PLAINTEXT", "9094 SASL_SSL"],
  ["Topic creation", "6 partitions, min ISR 1", "12 partitions, min ISR 2"],
  ["Disk capacity", "page at 90%", "page at 85%"],
  ["Schema registry", "port 8081, BACKWARD", "port 8085, FULL_TRANSITIVE"],
  ["On-call escalation", "ack 15 min, kafka-ops", "ack 5 min, streaming-platform-prod"]];
s.addTable([[hdr("Subject"), hdr("Old version says"), hdr("Current version says")],
  ...rows3.map((r, i) => r.map((c, j) => ({ text: c, options: { fontSize: 13,
    color: j === 1 ? HEX.accent2 : j === 2 ? HEX.dk2 : HEX.dk1, bold: j > 0,
    fill: { color: i % 2 ? HEX.lt1 : HEX.lt2 } } })))],
  { x: M, y: 1.55, w: 8.3, colW: [2.3, 2.9, 3.1], rowH: 0.47, border: { type: "none" }, margin: [0.04, 0.12, 0.04, 0.12] });
card(s, 9.25, 1.55, 3.45, 4.23, HEX.accent5, "design rules");
T(s, "Built so the trap is real", { x: 9.5, y: 1.75, w: 3.0, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
T(s, [
  { text: "One template per pair: only facts differ", options: { bullet: true, breakLine: true } },
  { text: "No \"superseded\" banner in old files", options: { bullet: true, breakLine: true } },
  { text: "No front-matter: metadata lives in the manifest", options: { bullet: true, breakLine: true } },
  { text: "Fictional company Halcyon, not Meridian or Aventro", options: { bullet: true } }],
  { x: 9.5, y: 2.25, w: 3.0, h: 2.45, fontSize: 14, color: C.text1, paraSpaceAfter: 6, valign: "top" });
T(s, "4 / 8", { x: 9.5, y: 4.75, w: 1.5, h: 0.75, fontSize: 32, bold: true, color: C.accent2, fontFace: THEME.headFontFace, valign: "middle" });
T(s, "plain questions where the old file ranks first", { x: 11.0, y: 4.75, w: 1.55, h: 0.8, fontSize: 12, color: C.text1, valign: "middle" });
T(s, "Test: python simple_rag/b1_check.py   →   16 files, 8 pairs, similarity 0.87–0.97, old ranks first 4/8   ·   PASS",
  { x: M, y: 6.4, w: 12.1, h: 0.4, fontSize: 12, color: C.accent4 });
s.addNotes("Each pair has 5 to 9 conflicting values. A few values are deliberately identical in both versions, such as replication factor 3 and /var/lib/kafka. Those feed the exact-string tests that must stay flat. The generator in tools/make_corpus.py recreates every file byte for byte.");

// ── 8. step 4 ────────────────────────────────────────────────────────────────
s = content("Steps 2–12", "Step 4: the manifest says which file is current");
card(s, M, 1.6, 6.0, 4.54, HEX.dk1, "json card");
T(s, [
  { text: '"disk-capacity.md": {', options: { breakLine: true } },
  { text: '  "doc": "Kafka Broker Disk',  options: { breakLine: true } },
  { text: '          Capacity Runbook",', options: { breakLine: true } },
  { text: '  "version": 3,', options: { breakLine: true } },
  { text: '  "effective_date": "2026-05-01",', options: { breakLine: true } },
  { text: '  "superseded": false', options: { breakLine: true, color: HEX.accent5, bold: true } },
  { text: "}", options: { breakLine: true } },
  { text: '"disk-capacity-2025.md": { … v2,', options: { breakLine: true } },
  { text: '  "superseded": true }', options: { color: "F7B98A", bold: true } }],
  { x: M + 0.35, y: 1.8, w: 5.4, h: 4.15, fontSize: 17, color: HEX.lt1, fontFace: "Courier New", valign: "middle", lineSpacingMultiple: 1.15 });
const f4 = [["doc", "Title shared by both versions: links the pair"], ["version", "Integer; higher is newer"],
  ["effective_date", "YYYY-MM-DD; matches the file header"], ["superseded", "true once a newer version exists. The filter uses only this"]];
f4.forEach(([k, d], i) => {
  const y = 1.6 + i * 1.18;
  card(s, 7.0, y, 5.7, 1.0, i === 3 ? HEX.accent6 : HEX.lt2, `field ${k}`, i === 3 ? HEX.accent2 : null);
  T(s, k, { x: 7.25, y: y + 0.1, w: 5.2, h: 0.38, fontSize: 15, bold: true, color: C.text1, fontFace: "Courier New" });
  T(s, d, { x: 7.25, y: y + 0.5, w: 5.2, h: 0.4, fontSize: 13, color: C.text1 });
});
T(s, "Test: b1_check.py → 16 entries, 8 current / 8 superseded, 64 conflict values verified · negative test FAIL (5) as intended",
  { x: M, y: 6.4, w: 12.1, h: 0.4, fontSize: 12, color: C.accent4 });
s.addNotes("Metadata lives outside the documents so the embedded text is exactly what a reader sees. The manifest is written by the same generator as the runbooks, so they cannot drift. The conflicts block lists all 64 differing values and is used to write test cases, never given to the retriever.");

// ── 9. step 5 ────────────────────────────────────────────────────────────────
s = content("Steps 2–12", "Step 5: 21 questions, written before the fix");
// Drawn bars, not a native chart: Keynote (the only presentation app on this Mac) does not render pptxgenjs charts.
T(s, "Cases by type", { x: M, y: 1.6, w: 5.6, h: 0.4, fontSize: 16, bold: true, color: C.text1 });
const bars = [["superseded", 9, "old vs current conflict", HEX.accent2], ["exact_string", 7, "exact value must be found", HEX.accent1],
  ["multi_hop", 3, "needs two current docs", HEX.dk2], ["unanswerable", 2, "nothing to invent", HEX.accent4]];
bars.forEach(([lbl, n, d, col], i) => {
  const y = 2.25 + i * 0.98;
  T(s, lbl, { x: M, y, w: 1.75, h: 0.4, fontSize: 15, bold: true, color: C.text1, fontFace: "Courier New", valign: "middle" });
  T(s, d, { x: M, y: y + 0.4, w: 1.85, h: 0.35, fontSize: 11, color: C.accent4 });
  s.addShape(pres.shapes.RECTANGLE, { x: M + 1.95, y: y + 0.05, w: n * 0.33, h: 0.6, fill: { color: col }, line: { type: "none" }, objectName: `bar ${lbl}` });
  T(s, String(n), { x: M + 2.05 + n * 0.33, y: y + 0.05, w: 0.6, h: 0.6, fontSize: 20, bold: true, color: C.text1, valign: "middle" });
});
T(s, "21 cases, all 8 current runbooks covered", { x: M, y: 6.05, w: 5.6, h: 0.3, fontSize: 12, color: C.accent4 });
card(s, 6.55, 1.55, 6.15, 2.75, HEX.lt2, "example case");
T(s, "kafka-001 · superseded", { x: 6.8, y: 1.72, w: 5.7, h: 0.35, fontSize: 13, bold: true, color: C.accent4 });
T(s, "\"Broker 4's data volume just hit 87%. Should that have paged someone?\"",
  { x: 6.8, y: 2.1, w: 5.7, h: 0.85, fontSize: 17, italic: true, color: C.text1 });
T(s, [
  { text: "Pass: ", options: { bold: true, color: HEX.accent1 } }, { text: "yes, the page line is 85%", options: { breakLine: true } },
  { text: "Must cite: ", options: { bold: true } }, { text: "disk-capacity.md (v3)", options: { breakLine: true } },
  { text: "Must not cite / say: ", options: { bold: true, color: HEX.accent2 } }, { text: "the 2025 file, \"90%\"" }],
  { x: 6.8, y: 3.05, w: 5.7, h: 1.5, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 4 });
T(s, [
  { text: "87% sits between old and new thresholds, so the versions give opposite answers.", options: { bullet: true, breakLine: true } },
  { text: "Stale values are banned as literal strings: no LLM judge needed.", options: { bullet: true, breakLine: true } },
  { text: "Paraphrase check caught one copied question before the freeze.", options: { bullet: true } }],
  { x: 6.55, y: 4.6, w: 6.15, h: 1.6, fontSize: 15, color: C.text1, paraSpaceAfter: 6, valign: "top" });
T(s, "Test: b1_check.py → all cites resolve, banned strings only in old files, exact values verbatim · negative test FAIL (4) as intended",
  { x: M, y: 6.4, w: 12.1, h: 0.4, fontSize: 12, color: C.accent4 });
s.addNotes("Superseded cases test the fix. Exact-string cases must stay flat, which proves the filter didn't break normal retrieval. Multi-hop cases need two current documents. Unanswerable cases check the model doesn't start guessing. The set is written but not yet frozen: that is Step 6.");

// ── Step 7 results ───────────────────────────────────────────────────────────
s = content("Steps 2–12", "Step 7: the baseline proves the problem");
card(s, M, 1.55, 4.6, 4.75, HEX.accent6, "headline", HEX.accent2);
T(s, "Superseded chunks retrieved", { x: M + 0.3, y: 1.8, w: 4.0, h: 0.4, fontSize: 16, bold: true, color: C.text1 });
T(s, "48.8%", { x: M + 0.3, y: 2.3, w: 4.0, h: 1.4, fontSize: 72, bold: true, color: C.accent2, fontFace: THEME.headFontFace });
T(s, "41 of 84 retrieved chunks are outdated: half of what the LLM would read.", { x: M + 0.3, y: 3.85, w: 4.0, h: 0.9, fontSize: 15, color: C.text1 });
T(s, "Filter OFF · unchanged retriever · k = 4 · 21 frozen cases", { x: M + 0.3, y: 5.5, w: 4.0, h: 0.6, fontSize: 12, color: C.accent4 });
const s7 = [["0 / 9", "superseded cases pass", "old twin retrieved every time", HEX.accent2],
  ["7 / 7", "exact-string cases pass", "must stay 7/7 after the fix", HEX.accent1],
  ["0 / 3", "multi-hop cases pass", "old twins crowd out the 2nd doc", HEX.accent2],
  ["144 ms", "median retrieval", "embed query + Chroma search", HEX.dk1]];
s7.forEach(([n, l, d, col], i) => {
  const x = 5.55 + (i % 2) * 3.6, y = 1.55 + Math.floor(i / 2) * 2.45;
  card(s, x, y, 3.4, 2.25, HEX.lt2, `stat ${l}`);
  T(s, n, { x: x + 0.25, y: y + 0.2, w: 2.9, h: 0.9, fontSize: 40, bold: true, color: col, fontFace: THEME.headFontFace });
  T(s, l, { x: x + 0.25, y: y + 1.15, w: 2.9, h: 0.4, fontSize: 15, bold: true, color: C.text1 });
  T(s, d, { x: x + 0.25, y: y + 1.55, w: 2.9, h: 0.5, fontSize: 13, color: C.accent4 });
});
T(s, "Test: b1_eval.py --off → results/baseline_filter_off.json · commit 8c97952 · re-run gives identical cases and numbers",
  { x: M, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("rag.py only gained two settings to point at the Kafka corpus; retrieval is the original. b1_eval.py looks up each retrieved file in the manifest. Example: for 'Broker 4 hit 87%', the retriever returned disk-capacity.md AND disk-capacity-2025.md. This is the number the filter must take to 0% without moving exact-string off 7/7.");

// ── Step 8 results ───────────────────────────────────────────────────────────
s = content("Steps 2–12", "Step 8: every chunk in Chroma now knows its version");
card(s, M, 1.55, 5.7, 4.75, HEX.lt2, "chroma rows");
T(s, "Inside Chroma (b1_check.py --chroma)", { x: M + 0.25, y: 1.7, w: 5.2, h: 0.4, fontSize: 15, bold: true, color: C.text1 });
const crow = [["disk-capacity#0", "3", "2026-05-01", "False"], ["disk-capacity-2025#0", "2", "2025-02-01", "True"],
  ["schema-registry#0", "2", "2026-03-20", "False"], ["schema-registry-2024#0", "1", "2024-07-15", "True"],
  ["… 13 more", "", "", ""]];
s.addTable([[hdr("chunk"), hdr("ver"), hdr("effective"), hdr("superseded")],
  ...crow.map((r, i) => r.map((c, j) => ({ text: c, options: { fontSize: 12, fontFace: "Courier New",
    bold: j === 3, color: j === 3 ? (c === "True" ? HEX.accent2 : HEX.dk2) : HEX.dk1, fill: { color: i % 2 ? HEX.lt2 : HEX.lt1 } } })))],
  { x: M + 0.25, y: 2.2, w: 5.2, colW: [2.45, 0.55, 1.15, 1.05], rowH: 0.36, border: { type: "none" }, margin: [0.03, 0.06, 0.03, 0.06] });
T(s, [{ text: "17 / 17 ", options: { bold: true, color: HEX.accent1 } }, { text: "chunks carry all 4 fields, values = manifest", options: { breakLine: true } },
  { text: "9 / 8 ", options: { bold: true, color: HEX.accent1 } }, { text: "chunks from 8 current / 8 old files via where=…", options: { breakLine: true } },
  { text: "48.8% ", options: { bold: true, color: HEX.accent2 } }, { text: "OFF run unchanged: metadata alone changes nothing" }],
  { x: M + 0.25, y: 4.55, w: 5.2, h: 1.6, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 4 });
card(s, 6.55, 1.55, 6.15, 4.75, HEX.dk1, "filter demo");
T(s, "b1_inspect_chroma.py: \"Broker 4 … hit 87% …\"", { x: 6.8, y: 1.7, w: 5.7, h: 0.4, fontSize: 14, bold: true, color: HEX.lt1 });
const demo = [["Filter OFF (plain top-4)", [["disk-capacity.md", 0], ["disk-capacity-2025.md", 1], ["broker-rolling-restart-2025.md", 1], ["broker-rolling-restart.md", 0]]],
  ['Filter ON  where={"superseded": False}', [["disk-capacity.md", 0], ["broker-rolling-restart.md", 0], ["topic-retention.md", 0], ["consumer-lag-alerting.md", 0]]]];
demo.forEach(([lbl, rows], k) => {
  const y = 2.2 + k * 2.0;
  T(s, lbl, { x: 6.8, y, w: 5.7, h: 0.35, fontSize: 13, bold: true, color: "8FD8CC" });
  T(s, rows.map(([f, sup], i) => ({ text: `#${i + 1}  ${f}${sup ? "   SUPERSEDED" : ""}`,
    options: { breakLine: i < rows.length - 1, color: sup ? "F7B98A" : HEX.lt1, bold: !!sup } })),
    { x: 6.8, y: y + 0.38, w: 5.7, h: 1.45, fontSize: 13, fontFace: "Courier New", valign: "top" });
});
T(s, "Test: b1_check.py --no-trap --chroma → PASS · on the pre-Step-8 collection → FAIL (18) · commit 65ee770",
  { x: M, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("rag.py copies the manifest fields onto every chunk at ingest. The check reads Chroma directly, not rag.py. The demo runs one question against Chroma with and without the where clause: the 2025 disk runbook disappears. Step 9 puts exactly this clause into rag.retrieve().");

// ── Steps 9–10 results ───────────────────────────────────────────────────────
s = content("Steps 2–12", "Steps 9–10: one where-clause, behind a switch");
card(s, M, 1.55, 6.3, 4.75, HEX.dk1, "retrieve code");
T(s, [
  ["def retrieve(query, k=4, version_aware=False):", HEX.lt1],
  ["    ...", HEX.lt1],
  ["    if version_aware:      # ON", "8FD8CC"],
  ["        res = collection().query(", HEX.lt1],
  ["            query_embeddings=[qv], n_results=k,", HEX.lt1],
  ['            where={"superseded": False},', "F7B98A"],
  ["            include=[...])", HEX.lt1],
  ["    else:                  # OFF: original query", "8FD8CC"],
  ["        res = collection().query(", HEX.lt1],
  ["            query_embeddings=[qv], n_results=k,", HEX.lt1],
  ["            include=[...])", HEX.lt1]].map(([t, c], i, a) => ({ text: t, options: { color: c, breakLine: i < a.length - 1, bold: c === "F7B98A" } })),
  { x: M + 0.3, y: 1.75, w: 5.8, h: 4.35, fontSize: 14, fontFace: "Courier New", valign: "middle" });
const cmp = [["Superseded chunks", "48.8%", "0.0%"], ["Superseded cases", "0 / 9", "9 / 9"],
  ["Exact-string cases", "7 / 7", "7 / 7"], ["Multi-hop cases", "0 / 3", "3 / 3"], ["Median latency", "143.8 ms", "146.9 ms"]];
s.addTable([[hdr("Metric"), hdr("OFF"), hdr("ON (preview)")],
  ...cmp.map((r, i) => r.map((c, j) => ({ text: c, options: { fontSize: 14, bold: j > 0,
    color: j === 1 && i < 2 ? HEX.accent2 : j === 2 && i !== 4 ? HEX.dk2 : HEX.dk1, fill: { color: i % 2 ? HEX.lt1 : HEX.lt2 } } })))],
  { x: 7.15, y: 1.55, w: 5.55, colW: [2.45, 1.4, 1.7], rowH: 0.42, border: { type: "none" }, margin: [0.04, 0.1, 0.04, 0.1] });
card(s, 7.15, 4.3, 5.55, 2.0, HEX.accent6, "honest note", HEX.accent2);
T(s, [{ text: "Live LLM test (\"87% disk?\"): ", options: { bold: true, color: HEX.accent2 } },
  { text: "correct in both modes, but with the filter OFF the stale 90% runbook was #2 in the context. A right answer on stale context is luck; B1 removes the luck." }],
  { x: 7.35, y: 4.4, w: 5.15, h: 1.8, fontSize: 14, color: C.text1, valign: "middle" });
T(s, "Tests: OFF identical to the Step 7 baseline (21 cases, same files) · ON preview 0/84 · commit 3e269fd",
  { x: M, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("The only change to the query is the where clause, and only when version_aware is True. OFF is byte-for-byte the original query, which the identical OFF run proves. The formal AFTER run, committed to results/, is Step 11.");

// ── 10. testing ──────────────────────────────────────────────────────────────
pres.addSection({ title: "Testing" });
s = content("Testing", "Every step has a test, and every test is tested");
const tests = [
  ["3", "Corpus", "16 files, 8 pairs, no banners; similarity trap measured", "PASS", "—"],
  ["4", "Manifest", "4 typed fields, 1 current per doc, 64 conflicts in their files", "PASS", "FAIL (5) on 3 injected errors"],
  ["5", "Golden set", "cites resolve, banned strings old-only, values verbatim, paraphrased", "PASS", "FAIL (4) on 2 injected errors"],
  ["7", "BEFORE run", "48.8% superseded; rerun identical; --on refuses until built", "DONE", "—"],
  ["8", "Chroma", "17/17 chunks tagged; where-filter splits 8/8 files; OFF unchanged", "PASS", "FAIL (18) before re-ingest"],
  ["9–10", "Filter", "OFF identical to baseline; ON preview 0.0%, exact 7/7", "PASS", "—"],
  ["11–12", "AFTER + report", "0.0% · 9/9 · 7/7 · 3/3; fair latency +0.9 ms", "PASS", "—"]];
s.addTable([[hdr("Step"), hdr("Checks"), hdr("What is verified"), hdr("Real data"), hdr("Negative test")],
  ...tests.map((r, i) => r.map((c, j) => ({ text: c, options: { fontSize: 13, bold: j === 3 || j === 1,
    color: j === 3 ? (c === "PASS" || c === "DONE" ? HEX.accent1 : HEX.accent4) : j === 4 && c !== "—" ? HEX.accent2 : HEX.dk1,
    fill: { color: i % 2 ? HEX.lt1 : HEX.lt2 }, valign: "middle" } })))],
  { x: M, y: 1.55, w: 12.1, colW: [0.9, 1.6, 5.4, 1.4, 2.8], rowH: 0.45, border: { type: "none" }, margin: [0.05, 0.12, 0.05, 0.12] });
card(s, M, 5.55, 12.1, 0.95, HEX.accent5, "negative test idea", HEX.accent1);
T(s, [{ text: "Negative test: ", options: { bold: true, color: HEX.dk2 } },
  { text: "break the data on purpose (mark an old file current, ban the right answer), run the checks, confirm they FAIL, then restore. A check that never fails proves nothing." }],
  { x: M + 0.3, y: 5.57, w: 11.5, h: 0.9, fontSize: 14, color: C.text1, valign: "middle" });
s.addNotes("b1_check.py grows with each step and runs in one command. Each layer was also proven to catch mistakes by injecting errors. The ablation checks arrive with b1_eval.py in Step 7.");

// ── test plan ────────────────────────────────────────────────────────────────
s = content("Testing", "30 copy-paste test cases, all passing");
const areas = [["A", "Setup", "3", "prereqs · clone · venv"], ["B", "Data", "3", "consistency · trap · fingerprints"],
  ["C", "Chroma", "4", "ingest · metadata · raw query · filter demo"], ["D", "Ablation", "6", "OFF · ON · per case · determinism · latency"],
  ["E", "LLM answers", "6", "stale threshold · exact value · unanswerable"], ["F", "Negative", "3", "broken manifest · golden · Chroma"],
  ["G", "Scenarios", "2", "wrong flag · publish new version"], ["H", "Project", "3", "freeze proof · no secrets · full rebuild"]];
areas.forEach(([l, t, n, d], i) => {
  const x = M + (i % 4) * 3.05, y = 1.55 + Math.floor(i / 4) * 1.55;
  card(s, x, y, 2.85, 1.35, i === 4 ? HEX.accent6 : HEX.lt2, `area ${l}`);
  T(s, `${l}. ${t}`, { x: x + 0.2, y: y + 0.12, w: 1.9, h: 0.4, fontSize: 15, bold: true, color: C.text1 });
  T(s, n, { x: x + 2.05, y: y + 0.08, w: 0.6, h: 0.5, fontSize: 24, bold: true, color: C.accent1, align: "right", fontFace: THEME.headFontFace });
  T(s, d, { x: x + 0.2, y: y + 0.6, w: 2.5, h: 0.65, fontSize: 12, color: C.text1, valign: "top" });
});
codeCard(s, 4.75, 1.0, [["python3 b1-track-b/tools/tests/run_tests.py --shell zsh     # → 30 PASS · 0 FAIL", ""]], 15);
T(s, [{ text: "Each case: ", options: { bold: true } }, { text: "purpose · commands to paste · expected message · pass rule. " },
  { text: "Verified 2026-10-18 from a fresh GitHub clone in zsh and bash. ", options: { bold: true, color: HEX.dk2 } },
  { text: "PDF: b1-track-b/docs/B1_TrackB_Kafka_Test-Scenarios_v1_2026-10-18.pdf" }],
  { x: M, y: 5.95, w: 12.1, h: 0.75, fontSize: 13, color: C.text1, valign: "top" });
s.addNotes("The test plan and the runner come from one spec file, so the PDF can't drift from what was executed. LLM-dependent cases (E) are judged on meaning; the runner reports wording differences as WARN.");

// ── 11. next ─────────────────────────────────────────────────────────────────
s = content("Testing", "Steps 11–12: the result");
const nxt = [["7", "BEFORE ✓", "48.8% superseded"], ["8", "Metadata ✓", "17/17 chunks tagged"],
  ["9–10", "Filter ✓", "OFF = baseline"], ["11", "AFTER ✓", "0.0% superseded"], ["12", "Report ✓", "table + conclusion"]];
nxt.forEach(([n, t, d], i) => {
  const x = M + i * 2.48;
  circle(s, x + 0.72, 1.7, 0.85, HEX.accent1, n, HEX.lt1, `next ${n}`);
  T(s, t, { x, y: 2.7, w: 2.3, h: 0.45, fontSize: 18, bold: true, align: "center", color: C.text1 });
  T(s, d, { x, y: 3.15, w: 2.3, h: 0.7, fontSize: 13, align: "center", color: C.text1 });
  if (i < 4) arrow(s, x + 1.67, 2.125, x + 3.12, 2.125, `next arrow ${i}`);
});
const targets = [["Superseded chunks retrieved", "48.8% (41/84)", "0.0% (0/84)"], ["Superseded / multi-hop passed", "0/9 · 0/3", "9/9 · 3/3"],
  ["Exact-string cases passed", "7 / 7", "7 / 7 (flat)"], ["Latency (105 calls each, fair)", "50.2 ms", "51.1 ms"]];
s.addTable([[hdr("Metric"), hdr("Filter OFF (before)"), hdr("Filter ON (after)")],
  ...targets.map((r, i) => r.map((c, j) => ({ text: c, options: { fontSize: 14, bold: j > 0,
    color: j === 2 ? HEX.dk2 : HEX.dk1, fill: { color: i % 2 ? HEX.lt1 : HEX.lt2 } } })))],
  { x: M, y: 4.2, w: 8.5, colW: [3.9, 2.3, 2.3], rowH: 0.42, border: { type: "none" }, margin: [0.04, 0.12, 0.04, 0.12] });
card(s, 9.4, 4.2, 3.3, 2.1, HEX.accent6, "rule card", HEX.accent2);
T(s, [{ text: "Conclusion", options: { bold: true, breakLine: true, color: HEX.accent2 } },
  { text: "One where-clause on version metadata: stale context 48.8% → 0%, exact-string flat, < 1 ms." }],
  { x: 9.6, y: 4.3, w: 2.9, h: 1.9, fontSize: 16, color: C.text1, valign: "middle", paraSpaceAfter: 6 });
s.addNotes("Steps 11 and 12: the same 21 frozen cases with the filter ON, committed; then a fair latency test (OFF and ON interleaved, 105 calls each) and the ablation table. No case fails with the filter ON; the 2 unanswerable cases are not scored on retrieval.");

// ── 12. how to run ───────────────────────────────────────────────────────────
s = content("Testing", "How to run and test it yourself");
card(s, M, 1.55, 12.1, 3.55, HEX.dk1, "commands");
const cmds = [
  ["# start every session", "comment"],
  ["B=~/Desktop/AI-Architect_L2_Aug_2026/project_10082026", ""],
  ["cd $B/track-b-kafka && source $B/mai-practitioner-labs/.venv/bin/activate", ""],
  ["", ""],
  ["# data tests (Steps 3–5)", "comment"],
  ["python simple_rag/b1_check.py            # full, with similarity trap", ""],
  ["python simple_rag/b1_check.py --no-trap  # fast", ""],
  ["", ""],
  ["# recreate the corpus from scratch (byte-identical)", "comment"],
  ["python $B/b1-tracking/track-b/tools/make_corpus.py simple_rag/corpus/kafka", ""]];
T(s, cmds.map(([t, k], i) => ({ text: t || " ", options: { breakLine: i < cmds.length - 1,
  color: k === "comment" ? "8FD8CC" : HEX.lt1 } })),
  { x: M + 0.35, y: 1.75, w: 11.4, h: 3.2, fontSize: 15, fontFace: "Courier New", valign: "middle" });
card(s, M, 5.3, 12.1, 0.95, HEX.accent5, "expected output", HEX.accent1);
T(s, [{ text: "Expected: ", options: { bold: true, color: HEX.dk2 } },
  { text: "every line starts with OK and the last line is PASS (exit code 0). A FAIL line names the file and what is wrong." }],
  { x: M + 0.3, y: 5.35, w: 11.5, h: 0.85, fontSize: 15, color: C.text1, valign: "middle" });
T(s, "Every command: SOP v7 PDF, Appendix A  ·  Driving Claude Code: Claude-CLI Run Guide PDF (both in docs/)",
  { x: M, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("These commands work from any terminal on this Mac. Each command's expected output is in the SOP, in the Verify and Expect parts of each step.");

// ── GitHub ───────────────────────────────────────────────────────────────────
pres.addSection({ title: "GitHub" });
s = content("GitHub", "Where the code lives: one public repo, three branches");
card(s, M, 1.5, 12.1, 0.8, HEX.dk1, "repo url");
T(s, [{ text: "github.com/", options: { color: "8FD8CC" } }, { text: "shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware", options: { color: HEX.lt1, bold: true } },
  { text: "   · public", options: { color: "8FD8CC" } }],
  { x: M + 0.3, y: 1.5, w: 11.5, h: 0.8, fontSize: 18, fontFace: "Courier New", valign: "middle" });
const br = [["main", "Overview README", "Start here: what B1 is, the result, links to every branch and doc", HEX.lt2, null],
  ["track-b-kafka-version-aware", "The full project", "Class base 6b918c2 + one commit per step (3–12), results, b1-track-b/ docs and rebuild tools", HEX.accent5, HEX.accent1],
  ["rag-deployment", "Runnable package", "Only what the finished version-aware RAG needs, plus run.sh: setup · ingest · check · eval · ask", HEX.accent6, HEX.accent2]];
br.forEach(([b, t, d, fill, line], i) => {
  const x = M + i * 4.1;
  card(s, x, 2.55, 3.85, 1.95, fill, `branch ${b}`, line);
  T(s, b, { x: x + 0.2, y: 2.7, w: 3.45, h: 0.45, fontSize: 13, bold: true, color: C.text1, fontFace: "Courier New" });
  T(s, t, { x: x + 0.2, y: 3.15, w: 3.45, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
  T(s, d, { x: x + 0.2, y: 3.6, w: 3.45, h: 0.85, fontSize: 13, color: C.text1, valign: "top" });
});
T(s, [{ text: "Track A ", options: { bold: true } }, { text: "(front-matter version) stays in github.com/shreenathacc22/L2-RAG-B1-version-aware-retrieval · main", options: { breakLine: true } },
  { text: "Never published: ", options: { bold: true, color: HEX.accent2 } }, { text: ".env and .env.* (API key), raw run logs (local paths), personal email (commits use the GitHub noreply address)." }],
  { x: M, y: 4.85, w: 12.1, h: 0.95, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 4 });
s.addNotes("Clone a branch with: git clone -b <branch> https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware.git. The rag-deployment branch runs on its own; the project branch carries the full history and the docs.");

s = content("GitHub", "Get it and run it");
codeCard(s, 1.5, 4.85, [
  ["# the runnable RAG                                     expect:", "c"],
  ["git clone -b rag-deployment \\", ""],
  ["  https://github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware.git b1-rag", ""],
  ["cd b1-rag", ""],
  ["./run.sh setup          # Python 3.12 venv + packages", ""],
  ["./run.sh ingest         # 17 chunks with version metadata", ""],
  ["./run.sh check          # data + Chroma checks: PASS", ""],
  ["./run.sh eval           # OFF 48.8% -> ON 0.0%", ""],
  ['./run.sh ask "What port is the schema registry on?"   # needs .env (README)', ""],
  ["", ""],
  ["# the full project, then rebuild every step", "c"],
  ["git clone -b track-b-kafka-version-aware <repo-url> b1-project && cd b1-project", ""],
  ["SKIP_STEP2=1 bash b1-track-b/tools/recreate_track_b.sh ../track-b-rebuild", ""]], 13.5);
T(s, "Docs on the project branch: b1-track-b/docs/ (SOP PDF, Claude-CLI Run Guide PDF, this deck).",
  { x: M, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("ask needs an OpenAI-compatible key in .env (OPENAI_API_KEY, OPENAI_BASE_URL, MODEL); everything else runs offline.");

// ── 13–15. recreate without Claude ───────────────────────────────────────────
function codeCard(s, y, h, lines, size) {
  card(s, M, y, 12.1, h, HEX.dk1, "code");
  T(s, lines.map(([t, k], i) => ({ text: t || " ", options: { breakLine: i < lines.length - 1,
    color: k === "c" ? "8FD8CC" : HEX.lt1 } })),
    { x: M + 0.35, y: y + 0.15, w: 11.4, h: h - 0.3, fontSize: size, fontFace: "Courier New", valign: "middle" });
}
pres.addSection({ title: "Recreate without Claude" });
s = content("Recreate without Claude", "Rebuild Steps 0–12 with one command");
codeCard(s, 1.5, 2.2, [
  ["B=~/Desktop/AI-Architect_L2_Aug_2026/project_10082026", ""],
  ["T=$B/b1-tracking/track-b/tools", ""],
  ["bash $T/recreate_track_b.sh                   # builds $B/track-b-rebuild", ""],
  ["VENV=$B/mai-practitioner-labs/.venv bash $T/recreate_track_b.sh   # faster: reuse Python", ""],
  ["SKIP_STEP2=1 bash $T/recreate_track_b.sh      # skip lab run: no proxy key needed", ""]], 15);
const chips = ["Clone 6b918c2", "Python env", "Step 2 lab", "Steps 3–4 data", "Step 5 + neg. tests", "Step 6 freeze", "Step 7 BEFORE", "Step 8 Chroma", "Steps 9–10 filter", "Steps 11–12", "Verify"];
chips.forEach((t, i) => {
  const x = M + i * 1.11;
  const last = i === chips.length - 1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.05, w: 0.99, h: 0.75, rectRadius: 0.1, objectName: `chip ${i}`,
    fill: { color: last ? HEX.accent5 : HEX.lt2 }, line: last ? { color: HEX.accent1, width: 1.5 } : { type: "none" } });
  T(s, t, { x: x + 0.02, y: 4.05, w: 0.95, h: 0.75, fontSize: 10, bold: true, align: "center", valign: "middle", color: C.text1 });
  if (!last) arrow(s, x + 1.0, 4.425, x + 1.1, 4.425, `chip arrow ${i}`);
});
card(s, M, 5.1, 12.1, 1.2, HEX.accent5, "tested", HEX.accent1);
T(s, [{ text: "Tested 2026-10-18:  ", options: { bold: true, color: HEX.dk2 } },
  { text: "210 s · every check OK · 3 negative tests FAIL as intended · BEFORE 48.8% · OFF unchanged after Steps 8 and 10 · AFTER 0.0% · 7 / 7 fingerprints MATCH. " },
  { text: "Stops at the first failure; never touches track-b-kafka/.", options: { italic: true } }],
  { x: M + 0.3, y: 5.15, w: 11.5, h: 1.1, fontSize: 15, color: C.text1, valign: "middle" });
s.addNotes("recreate_track_b.sh rebuilds everything up to the freeze in a separate folder and compares fingerprints of the corpus, manifest, golden set and check script with the original. If all four match, the rebuild is byte-identical. Logs go to the folder name plus .logs.");

s = content("Recreate without Claude", "Every command: Steps 0–2");
codeCard(s, 1.5, 4.85, [
  ["# Step 0 · get the code", "c"],
  ["B=~/Desktop/AI-Architect_L2_Aug_2026/project_10082026; T=$B/b1-tracking/track-b/tools", ""],
  ["cd $B && git clone https://github.com/balajivis/mai-practitioner-labs.git track-b-kafka", ""],
  ["cd track-b-kafka && git checkout 6b918c2 && git switch -c track-b", ""],
  ["cp $B/.env .env && chmod 600 .env                 # proxy key, never committed", ""],
  ["", ""],
  ["# Python 3.12 environment (once)", "c"],
  ["uv venv --python 3.12 .venv && source .venv/bin/activate", ""],
  ["uv pip install -r requirements.txt \\", ""],
  ['   "torch==2.2.2" "numpy<2" "transformers<5" "sentence-transformers<6"', ""],
  ["", ""],
  ["# Step 2 · the unchanged lab                     expect:", "c"],
  ["python simple_rag/rag.py ingest                   # ~196 vectors stored", ""],
  ['python simple_rag/rag.py ask "how do I tow my car?"   # answer with [1] [2] citations', ""],
  ["python simple_rag/rag.py eval                     # retrieval 2/6 · answer 2/6", ""]], 14.5);
T(s, "Already set up? Skip to Step 3: source $B/mai-practitioner-labs/.venv/bin/activate also works.",
  { x: M, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("Run in a fresh terminal. The expected result of each command is in its comment. The full version with explanations is SOP Appendix A.2.");

s = content("Recreate without Claude", "Every command: Steps 3–6");
codeCard(s, 1.5, 4.85, [
  ["# Steps 3–4 · corpus, manifest, data checks       expect:", "c"],
  ["python $T/make_corpus.py simple_rag/corpus/kafka   # wrote 16 runbooks + manifest.json", ""],
  ["cp $T/source/b1_check.py simple_rag/b1_check.py", ""],
  ["python simple_rag/b1_check.py                      # old outranks current 4/8 ... PASS", ""],
  ['git add simple_rag/corpus/kafka simple_rag/b1_check.py && git commit -m "Steps 3-4"', ""],
  ["", ""],
  ["# Step 5 · golden set", "c"],
  ["python $T/make_golden.py simple_rag/golden_kafka.jsonl   # wrote 21 cases", ""],
  ["python simple_rag/b1_check.py --no-trap                 # [Step 5] ... PASS", ""],
  ["", ""],
  ["# Step 6 · freeze, then prove it", "c"],
  ["git add simple_rag/golden_kafka.jsonl", ""],
  ['git commit -m "Freeze B1 golden set before version-aware retrieval"', ""],
  ["shasum simple_rag/golden_kafka.jsonl               # 850c67f2eab21aa1a6afabd481e5c3efccb7e0ba", ""]], 14.5);
T(s, "Negative tests and all four fingerprints: SOP Appendix A.2–A.3.",
  { x: M, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("make_corpus.py and make_golden.py are deterministic: they reproduce the committed files byte for byte, which the shasum line proves.");

s = content("Recreate without Claude", "Every command: Step 7");
codeCard(s, 1.5, 3.7, [
  ["# Step 7 · evaluator + BEFORE run (filter OFF)     expect:", "c"],
  ["cp $T/source/rag.py simple_rag/rag.py             # corpus settings only; retrieval unchanged", ""],
  ["cp $T/source/b1_eval.py simple_rag/b1_eval.py", ""],
  ["export RAG_CORPUS=simple_rag/corpus/kafka RAG_COLLECTION=kafka", ""],
  ["python simple_rag/rag.py ingest --formats md      # vectors stored 17", ""],
  ["python simple_rag/b1_eval.py --off                # superseded chunks 41/84 = 48.8%", ""],
  ["git add simple_rag/rag.py simple_rag/b1_eval.py simple_rag/results/", ""],
  ['git commit -m "B1 Track B step 7: evaluator and BEFORE baseline (filter OFF)"', ""]], 14.5);
card(s, M, 5.4, 12.1, 0.9, HEX.accent5, "step7 check", HEX.accent1);
T(s, [{ text: "Check: ", options: { bold: true, color: HEX.dk2 } },
  { text: "re-run b1_eval.py --off: every case and number except latency must be identical. --on must say \"not built yet\"." }],
  { x: M + 0.3, y: 5.45, w: 11.5, h: 0.8, fontSize: 15, color: C.text1, valign: "middle" });
s.addNotes("Two copied files and two commands. rag.py differs from upstream only by the RAG_CORPUS / RAG_COLLECTION settings and flat-folder loading.");

s = content("Recreate without Claude", "Every command: Step 8 and the Chroma tests");
codeCard(s, 1.5, 4.85, [
  ["# Step 8 · metadata into Chroma                     expect:", "c"],
  ["cp $T/source/step08/*.py simple_rag/", ""],
  ["python simple_rag/b1_check.py --no-trap --chroma  # FAIL (18): old collection, the negative test", ""],
  ["python simple_rag/rag.py ingest --formats md      # re-ingest: metadata goes in", ""],
  ["python simple_rag/b1_check.py --no-trap --chroma  # 17 chunks · 8 vs 8 files · PASS", ""],
  ["python simple_rag/b1_eval.py --off                # still 41/84 = 48.8%", ""],
  ["git add simple_rag/*.py && git commit -m \"B1 Track B step 8: metadata in Chroma\"", ""],
  ["", ""],
  ["# Look inside Chroma yourself", "c"],
  ["python simple_rag/b1_inspect_chroma.py            # all chunks + filter OFF vs ON demo", ""],
  ['python simple_rag/b1_inspect_chroma.py "What port is the schema registry on?"', ""],
  ["", ""],
  ["# Raw Chroma, no project scripts: SOP Step 8, Level 3", "c"]], 14);
T(s, "All three Chroma test levels, with expected output: SOP Step 8 \"How to test inside Chroma\".",
  { x: M, y: 6.45, w: 12.1, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("The first --chroma run is a deliberate negative test: before re-ingesting, the collection has no metadata, so the check must fail.");

s = content("Recreate without Claude", "Every command: Steps 9–10, the filter");
codeCard(s, 1.5, 3.9, [
  ["# Steps 9–10 · filter + OFF/ON switch                expect:", "c"],
  ["cp $T/source/step10/rag.py simple_rag/rag.py", ""],
  ["python simple_rag/b1_eval.py --off --out /tmp/b1check   # 41/84 = 48.8% (unchanged)", ""],
  ["python simple_rag/b1_eval.py --on  --out /tmp/b1check   # 0/84 = 0.0%, exact 7/7", ""],
  ['python simple_rag/rag.py ask "Broker 4 hit 87% disk. Page?"                 # stale #2', ""],
  ['python simple_rag/rag.py ask --version-aware "Broker 4 hit 87% disk. Page?" # current only', ""],
  ["git add simple_rag/rag.py", ""],
  ['git commit -m "B1 Track B steps 9-10: query-time version filter behind an OFF/ON switch"', ""]], 14);
card(s, M, 5.6, 12.1, 0.75, HEX.accent5, "step10 check", HEX.accent1);
T(s, [{ text: "Pass rule: ", options: { bold: true, color: HEX.dk2 } },
  { text: "OFF must equal the Step 7 baseline exactly; ON must show 0% superseded with exact_string unchanged." }],
  { x: M + 0.3, y: 5.62, w: 11.5, h: 0.7, fontSize: 15, color: C.text1, valign: "middle" });
s.addNotes("If OFF moves at all, something besides the filter changed and the ablation is invalid.");

s = content("Recreate without Claude", "Every command: Steps 11–12");
codeCard(s, 1.5, 4.0, [
  ["# Step 11 · AFTER run                                  expect:", "c"],
  ["shasum simple_rag/golden_kafka.jsonl               # 850c67f2... (unchanged)", ""],
  ["python simple_rag/b1_eval.py --on                  # 0/84 = 0.0% · 9/9 · 7/7 · 3/3", ""],
  ["git add simple_rag/results/ && git commit -m \"Step 11: AFTER run\"", ""],
  ["", ""],
  ["# Step 12 · fair latency, table, report", "c"],
  ["cp $T/source/step12/b1_eval.py simple_rag/", ""],
  ["python simple_rag/b1_eval.py --latency 5           # OFF ~50 ms, ON ~51 ms", ""],
  ["python simple_rag/b1_eval.py --table               # results/ablation_summary.md", ""],
  ["git add simple_rag/ && git commit -m \"Step 12: ablation table, fair latency and report\"", ""]], 14);
card(s, M, 5.7, 12.1, 0.65, HEX.accent5, "step12 check", HEX.accent1);
T(s, [{ text: "Result: ", options: { bold: true, color: HEX.dk2 } },
  { text: "superseded 48.8% → 0.0% · exact-string 7/7 → 7/7 · multi-hop 0/3 → 3/3 · latency +0.9 ms" }],
  { x: M + 0.3, y: 5.7, w: 11.5, h: 0.65, fontSize: 15, color: C.text1, valign: "middle" });
s.addNotes("--table reuses the committed OFF and ON results instead of rerunning them, so the BEFORE evidence never changes.");

// ── 16. close ────────────────────────────────────────────────────────────────
s = pres.addSlide({ masterName: "Title Dark", sectionTitle: "Recreate without Claude" });
s.addText("Done: stale retrieval 48.8% → 0%, exact-string flat", { placeholder: "title", bold: true, align: "left" });
s.addText("Public code: github.com/shreenathacc22/L2-RAG-B1-track-b-kafka-version-aware · branches main · track-b-kafka-version-aware · rag-deployment",
  { placeholder: "body" });
circle(s, M, 1.0, 0.7, HEX.accent1, "✓", HEX.lt1, "badge done");
s.addNotes("All 12 steps are complete and published. One-minute version: similarity alone served outdated runbooks for half the context; one query-time metadata filter removed them without hurting exact lookups or speed.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
