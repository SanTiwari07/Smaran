/* Smaran story: scroll-driven stages. No dependencies. */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  /* the prototype link: same origin when served together, the Vite port when the story is served alone */
  if (location.port === "5180") document.querySelectorAll(".open-dash").forEach((a) => (a.href = "http://localhost:5173/"));

  /* ---------- top progress bar ---------- */
  const bar = $("#progress");
  const onScroll = () => {
    const h = document.documentElement;
    bar.style.width = (h.scrollTop / (h.scrollHeight - h.clientHeight || 1)) * 100 + "%";
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ---------- generic stage visibility ---------- */
  function applyVisibility(stage, step) {
    $$("[data-from]", stage).forEach((el) => el.classList.toggle("hide", step < +el.dataset.from));
    $$("[data-only]", stage).forEach((el) => el.classList.toggle("hide", !el.dataset.only.split(" ").map(Number).includes(step)));
    $$("[data-upto]", stage).forEach((el) => el.classList.toggle("hide", step > +el.dataset.upto));
  }

  const handlers = {};
  $$(".scrolly").forEach((sc) => {
    const name = sc.dataset.chapter;
    const stage = $(".stage", sc);
    const steps = $$(".step", sc);
    let current = 0;
    const set = (i) => {
      if (i === current) return;
      current = i;
      steps.forEach((s, k) => s.classList.toggle("active", k === i - 1));
      applyVisibility(stage, i);
      handlers[name] && handlers[name](i, stage);
    };
    // the step nearest the vertical middle of the viewport is the active one
    const pick = () => {
      const mid = innerHeight * 0.52;
      let best = 0, bd = Infinity;
      steps.forEach((s, k) => {
        const r = s.getBoundingClientRect();
        if (r.bottom < 0 || r.top > innerHeight) return;
        const d = Math.abs((r.top + r.bottom) / 2 - mid);
        if (d < bd) { bd = d; best = k + 1; }
      });
      if (best) set(best);
    };
    addEventListener("scroll", pick, { passive: true });
    addEventListener("resize", pick);
    // initial state: nothing active until the section is near; still render step 0 as "all hidden"
    applyVisibility(stage, 0);
    handlers[name] && handlers[name](0, stage);
    pick();
  });

  /* ---------- 01 problem ---------- */
  handlers.problem = (i) => {
    const down = i >= 1 && i <= 2;
    const lb = $("#linkbar");
    lb.className = "link-bar " + (i === 0 ? "" : down ? "down" : "up");
    $("#link-t").textContent = i === 0 ? "relay in view" : down ? "on the surface" : "relay rises · syncing by timestamp";
    const pl = $("#p-link");
    pl.textContent = i === 0 || i >= 3 ? "relay in view" : "on the surface";
    pl.className = "pill " + (down ? "surface" : "ok");
    ["#p-a", "#p-b"].forEach((id) => {
      const p = $(id);
      p.textContent = down ? "on the surface · working" : "relay in view";
      p.className = "pill " + (down ? "amber" : "ok");
    });
  };

  /* ---------- 02 shards ---------- */
  const shardCode = {
    1: `<span class="c"># Krypta: opened like any shard, but nothing ever reads it for sync</span>
shard = <span class="f">EdgeShard.create</span>(<span class="s">"runtime/device-A/krypta"</span>, config)
<span class="c"># decision.residency == "private"  ->  store here only.</span>
<span class="c"># no outbox row is written, so nothing can leave.</span>`,
    2: `shard.<span class="f">update</span>(UpdateOperation.<span class="f">upsert_points</span>([point]))
<span class="c"># point id = uuid5(op_id): writing twice is harmless</span>
shard.<span class="f">update</span>(UpdateOperation.<span class="f">set_payload</span>(
    point_ids=[pid], payload={<span class="s">"status"</span>: <span class="s">"superseded"</span>}))`,
    3: `<span class="c"># Agora: fleet knowledge, refreshed from the server's change feed</span>
<span class="k">for</span> p <span class="k">in</span> gateway.<span class="f">changes</span>(since=meta.last_server_seq):
    agora.<span class="f">update</span>(UpdateOperation.<span class="f">upsert_points</span>([p]))`,
    4: `config = <span class="f">EdgeConfig</span>(
    vectors={<span class="s">"dense"</span>: <span class="f">EdgeVectorParams</span>(size=384, distance=Distance.Cosine)},
    sparse_vectors={<span class="s">"bm25"</span>: <span class="f">EdgeSparseVectorParams</span>()})
<span class="c"># Edge has no background optimizer -> shard.optimize() on idle</span>`,
  };
  handlers.shards = (i, stage) => {
    $$(".shard", stage).forEach((s) => s.classList.toggle("on", +s.dataset.shard === i));
    $("#shard-code").innerHTML = shardCode[i] || shardCode[1];
  };

  /* ---------- 03 search ---------- */
  handlers.search = (i) => {
    $("#m1").style.width = i >= 4 ? "15.2%" : "0";
    const l = $("#s-lat");
    l.textContent = i >= 4 ? "3.04 ms p50" : "on the surface";
    l.className = "pill " + (i >= 4 ? "ok" : "");
  };

  /* ---------- 04 argus (interactive) ---------- */
  const RULES = {
    phone_in: /(?<![\d-])(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\d-])/,
    phone_intl: /\+\d{1,3}[\s-]?\d{3,5}[\s-]?\d{3,5}[\s-]?\d{0,5}\b/,
    email: /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/,
    aadhaar: /(?<![\d-])\d{4}[\s-]\d{4}[\s-]\d{4}(?![\d-])|(?<![\d-])\d{12}(?![\d-])/,
    pan: /\b[A-Z]{5}\d{4}[A-Z]\b/,
  };
  const findPii = (t) => Object.keys(RULES).filter((k) => RULES[k].test(t));
  const SAFETY = /(smoke|spark|fume|fire|burn|e-?stop|emergency|crack|guard|lockout|do not use|do not run)/i;
  const IMPORTANT = /(vibrat|leak|noise|grind|squeal|temp|pressure|drift|alarm|jam|down|fault)/i;
  const PRIVATE_W = /(my |i've|i am|wife|husband|salary|rent|emi|loan|appraisal|medical|leave|daughter|son |dizzy|shift swap|swap shifts|surgery)/i;
  const CHIT = /^(ok|okay|thx|thanks|thank you|lol|hi|hello|good (morning|night)|morning|will do|see you)\b|canteen|lunch|water bottle/i;
  const MACHINE = /\b[A-Z]{2,}(?:-[A-Z]+)*-\d+\b|\b(spindle|conveyor|coolant|hydraulic|bearing|belt|robot|press|lathe|cnc)\b/i;
  const FLEET = [
    "CNC-07 tool changer jammed replace gripper spring and re-teach positions",
    "Lubrication on CNC-07 done next due in 250 hours",
    "Replace worn drive belt on LATHE-03 with the spare",
  ];
  const tok = (t) => new Set(t.toLowerCase().match(/[a-z0-9-]+/g) || []);
  const jac = (a, b) => { const A = tok(a), B = tok(b); let n = 0; A.forEach((x) => B.has(x) && n++); return n / (A.size + B.size - n || 1); };

  function argus(text) {
    const t = text.trim();
    const hits = findPii(t);
    const crit = SAFETY.test(t) ? 2 : IMPORTANT.test(t) ? 1 : 0;
    const L = [
      { n: 1, title: "PII rules", state: "pass", detail: "no PII pattern matched, pass to the classifier" },
      { n: 2, title: "Classifier", state: "skipped", detail: "not reached" },
      { n: 3, title: "Dedup vs Agora", state: "skipped", detail: "not reached" },
    ];
    let dest = "sync";
    if (!t) return { L, dest: null };
    if (hits.length) {
      L[0] = { n: 1, title: "PII rules", state: "fired", detail: "matched: " + hits.join(", ") + " → private, confidence 1.0" };
      return { L, dest: "private" };
    }
    // layer 2 (simulated)
    let res, why;
    if (PRIVATE_W.test(t)) { res = "private"; why = "personal wording → private (0.9x)"; }
    else if (CHIT.test(t) || t.split(/\s+/).length <= 2) { res = "drop"; why = "chit-chat → drop (0.9x)"; }
    else if (MACHINE.test(t)) { res = "sync"; why = "machine fact → sync (0.9x)" + (crit === 2 ? "; safety keyword → safety-critical" : crit ? "; important" : ""); }
    else { res = "private"; why = "unsure, kept local by default"; }
    L[1] = { n: 2, title: "Classifier", state: "fired", detail: why };
    dest = res;
    if (res !== "sync") { L[2] = { n: 3, title: "Dedup vs Agora", state: "skipped", detail: "only synced notes are checked" }; return { L, dest }; }
    let best = 0, bm = "";
    FLEET.forEach((f) => { const j = jac(t, f); if (j > best) { best = j; bm = f; } });
    if (best >= 0.55) {
      L[1].state = "pass";
      L[2] = { n: 3, title: "Dedup vs Agora", state: "fired", detail: "near-duplicate of fleet memory (“" + bm.slice(0, 34) + "…”) → drop" };
      return { L, dest: "drop" };
    }
    L[2] = { n: 3, title: "Dedup vs Agora", state: "pass", detail: "no near-duplicate in the mirror → sync" };
    return { L, dest };
  }

  const SAMPLES = [
    "Call Meena on +91 98450 12345 about the spare parts order",
    "SMOKE from the PRESS-02 motor, hit the e-stop",
    "Lubrication on CNC-07 done, next due in 250 hours",
    "Canteen's biryani is great today",
    "Send my PF details to kavya.r@example.com",
    "CNC-12 spindle drive fan was clogged with dust, cleaned it",
    "My wife's surgery is on Monday so I need two days off",
  ];
  const inp = $("#argus-in");
  const chips = $("#chips");
  SAMPLES.forEach((s) => {
    const b = document.createElement("button");
    b.className = "chip"; b.type = "button"; b.textContent = s.length > 34 ? s.slice(0, 32) + "…" : s;
    b.onclick = () => { inp.value = s; render(); };
    chips.appendChild(b);
  });
  function render() {
    const r = argus(inp.value);
    $("#layers").innerHTML = r.L.map((l) =>
      `<div class="layer ${l.state === "fired" ? "fired" : l.state === "skipped" ? "skipped" : ""}"><span class="ix">${l.n}</span><div><b>${l.title}</b><small>${l.detail}</small></div><span class="pill ${l.state === "fired" ? "ok" : ""}">${l.state === "fired" ? "decided" : l.state === "skipped" ? "skipped" : "passed"}</span></div>`).join("");
    $$("#dest > div").forEach((d) => d.classList.toggle("on", d.dataset.d === r.dest));
  }
  inp.addEventListener("input", render);
  render();
  const presets = { 1: 0, 2: 1, 3: 2 };
  handlers.argus = (i) => { if (i in presets && i > 0) { inp.value = SAMPLES[presets[i]]; render(); } };

  /* ---------- 05 hermes ---------- */
  const NOTES = [
    { id: "a", t: "Lubrication done on CNC-07", c: 0 },
    { id: "b", t: "Oil puddle under PRESS-02", c: 1 },
    { id: "c", t: "SMOKE from PRESS-02 motor, e-stop hit", c: 2 },
    { id: "d", t: "LATHE-03 chatter gone", c: 0 },
    { id: "e", t: "CNC-12 back up", c: 0 },
  ];
  const CRIT = ["routine", "important", "safety-critical"];
  const CRITCLS = ["", "amber", "bad"];
  function hermes(i) {
    const order = i >= 2 ? [...NOTES].sort((x, y) => y.c - x.c) : NOTES;
    const state = {};   // id -> sent | crash | resent
    if (i >= 2) ["c", "b", "a"].forEach((k) => (state[k] = "sent"));
    if (i === 3) ["d", "e"].forEach((k) => (state[k] = "crash"));
    if (i >= 4) ["d", "e"].forEach((k) => (state[k] = "resent"));
    $("#h-q").innerHTML = order.map((n) => {
      const st = state[n.id];
      const cls = st === "sent" ? "sent" : st === "crash" ? "crash" : st === "resent" ? "resent" : "";
      const tail = st === "sent" ? '<span class="pill ok">acked</span>' : st === "crash" ? '<span class="pill bad">stored, no ack</span>' : st === "resent" ? '<span class="pill amber">resent · skipped as seen</span>' : `<span class="pill ${CRITCLS[n.c]}">${CRIT[n.c]}</span>`;
      return `<div class="item ${cls}"><span class="pill ${CRITCLS[n.c]}" style="min-width:24px;justify-content:center">${n.c}</span><span>${n.t}</span>${tail}</div>`;
    }).join("");
    const link = $("#h-link");
    link.textContent = i <= 1 ? "on the surface" : i === 3 ? "rover killed" : "relay pass";
    link.className = "pill " + (i <= 1 ? "surface" : i === 3 ? "bad" : "ok");
    $("#h-srv").innerHTML = (i >= 3 ? 5 : i >= 2 ? 3 : 0) + "<small>on Qdrant Server</small>";
    $("#h-dup").innerHTML = "0<small>duplicates</small>";
    $("#h-note").textContent = [
      "5 notes queued in write order. Illustrative run; the measured one is beat 5 in the demo.",
      "5 notes queued in write order. Illustrative run; the measured one is beat 5 in the demo.",
      "Critical drains first: 2 → 1 → 0. Sent in batches, each acked once stored.",
      "The next batch reached the gateway, but the device died before the ack. Outbox rows are still in SQLite.",
      "After restart the outbox resends them; the gateway has seen those op_ids and skips them. Server count stays 5.",
    ][i];
  }
  handlers.hermes = (i) => hermes(i);

  /* ---------- 06 themis ---------- */
  const cmp = (a, b) => {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    let ge = true, le = true;
    keys.forEach((k) => { const x = a[k] || 0, y = b[k] || 0; if (x < y) ge = false; if (x > y) le = false; });
    return ge && le ? "equal" : ge ? "after" : le ? "before" : "concurrent";
  };
  function resolve(vs) {
    const maximal = vs.filter((v) => !vs.some((w) => cmp(w.vv, v.vv) === "after"));
    const top = maximal.length === 1 ? "current" : "contested";
    const out = {};
    vs.forEach((v) => { out[v.id] = maximal.includes(v) ? top : "superseded"; });
    return out;
  }
  const fmt = (vv) => "{" + Object.entries(vv).map(([k, n]) => `${k}:${n}`).join(", ") + "}";
  function themis(i) {
    const V = {
      v1: { id: "v1", vv: { A: 1 } },
      v2: { id: "v2", vv: i >= 2 ? { B: 1 } : { A: 1, B: 1 } },
      v3: { id: "v3", vv: { A: 1, B: 1, G: 1 } },
    };
    const vs = i === 3 ? [V.v1, V.v2, V.v3] : [V.v1, V.v2];
    const st = resolve(vs);
    ["v1", "v2", "v3"].forEach((k) => {
      const el = $("#" + k);
      el.classList.toggle("hide", k === "v3" && i !== 3);
      el.classList.remove("cur", "cont", "super");
      if (st[k]) el.classList.add(st[k] === "current" ? "cur" : st[k] === "contested" ? "cont" : "super");
      $("#" + k + "-vv").textContent = fmt(V[k].vv);
    });
    $("#v2-t").textContent = "Spindle vibrating. Do not run.";
    const names = { equal: "equal", after: "newer", before: "older", concurrent: "concurrent" };
    const rel = cmp(V.v2.vv, V.v1.vv);
    const bad = Object.values(st).includes("contested");
    const b = $("#t-badge");
    b.textContent = i === 0 ? "–" : bad ? "contested" : "resolved";
    b.className = "pill " + (i === 0 ? "" : bad ? "amber" : "ok");
    let v = "";
    if (i === 1 || i === 0) v = `Meera's vector <b>${fmt(V.v2.vv)}</b> vs Ravi's <b>${fmt(V.v1.vv)}</b>: Meera's is <b>${names[rel]}</b>. Ravi's version is <b>superseded</b>.`;
    if (i === 2) v = `<b>${fmt(V.v2.vv)}</b> vs <b>${fmt(V.v1.vv)}</b>: each has seen a write the other hasn't. Verdict: <b>${names[rel]}</b>. Both stay <b>contested</b> until a human decides.`;
    if (i === 3) v = `The supervisor's <b>${fmt(V.v3.vv)}</b> is ≥ both, so it dominates them. Ravi's and Meera's versions become <b>superseded</b>, and stay in the history.`;
    if (i === 4) {
      const ab = resolve([V.v1, V.v2]), ba = resolve([V.v2, V.v1]);
      v = `Deliver A then B: <b>${ab.v1}, ${ab.v2}</b>. Deliver B then A: <b>${ba.v1}, ${ba.v2}</b>. Deliver A twice: <b>${resolve([V.v1, V.v1, V.v2]).v2}</b>. The answer depends on the set of versions, never on the order.`;
    }
    $("#t-verdict").innerHTML = v;
  }
  handlers.themis = (i) => themis(i);

  /* ---------- 07 server ---------- */
  const srvCode = {
    1: `client.<span class="f">upsert</span>(<span class="s">"smaran"</span>, [PointStruct(id=uuid5(op_id),
    vector={<span class="s">"dense"</span>: dense, <span class="s">"bm25"</span>: SparseVector(...)}, payload=payload)])
<span class="c"># sparse_vectors_config={"bm25": SparseVectorParams(modifier=Modifier.IDF)}</span>`,
    2: `GET /changes?since=<span class="f">last_server_seq</span>     <span class="c"># only points that changed</span>
<span class="c"># each has a server_seq (integer payload index) -> ordered, resumable</span>`,
    3: `client.<span class="f">query_points</span>(<span class="s">"smaran"</span>,
    prefetch=[Prefetch(query=dense, using=<span class="s">"dense"</span>, limit=2*n),
              Prefetch(query=sparse, using=<span class="s">"bm25"</span>, limit=2*n)],
    query=<span class="f">FusionQuery</span>(fusion=Fusion.RRF), limit=n)`,
    4: `<span class="c"># dense vector on the wire: base64 float16 instead of JSON floats</span>
<span class="c"># round-trip error &lt; 1e-3, cosine(original, decoded) &gt; 0.9999</span>`,
  };
  handlers.server = (i, stage) => {
    const on = { 1: ["fn1", "fa1", "fn2", "fa2", "fn3"], 2: ["fn3", "fn6", "fa4", "fn5", "fa3", "fn4"], 3: ["fn1", "fn3"], 4: ["fn1", "fa1", "fn2"] }[i] || [];
    $$(".node, .arrow", stage).forEach((n) => n.classList.toggle("on", on.includes(n.id)));
    $("#srv-code").innerHTML = srvCode[i] || srvCode[1];
    $$(".track > span", stage).forEach((s) => (s.style.width = i >= 4 ? s.dataset.w + "%" : "0"));
    $("#srv-code").classList.toggle("hide", i >= 4 && innerWidth < 900);
  };

  /* ---------- starfield in the hero ---------- */
  (() => {
    const cv = $("#stars"), cx = cv && cv.getContext("2d");
    if (!cx) return;
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let S = [];
    const size = () => {
      cv.width = cv.clientWidth; cv.height = cv.clientHeight;
      S = Array.from({ length: 140 }, () => ({ x: Math.random() * cv.width, y: Math.random() * cv.height * .7, r: Math.random() * 1.3 + .3, p: Math.random() * 6, d: Math.random() }));
    };
    size(); addEventListener("resize", size);
    const draw = () => {
      cx.clearRect(0, 0, cv.width, cv.height);
      const t = still ? 0 : Date.now() / 1000;
      for (const s of S) {
        const x = (((s.x - t * 3 * s.d) % cv.width) + cv.width) % cv.width;
        cx.globalAlpha = (.3 + .45 * Math.abs(Math.sin(t * .8 + s.p))) * (1 - s.y / (cv.height * .85));
        cx.fillStyle = "#f5f1ea"; cx.beginPath(); cx.arc(x, s.y, s.r, 0, 7); cx.fill();
      }
      if (!still) requestAnimationFrame(draw);
    };
    draw();
  })();

  /* ---------- the sky shifts with the mission stage: dusk, dust haze, dawn, clear, daylight ---------- */
  (() => {
    const sky = $("#sky");
    const tints = { top: "#2a1116", problem: "#3a1a12", shards: "#241018", search: "#1a1220", argus: "#241018", hermes: "#4a2214", themis: "#3a2a1a", server: "#2a1a20", proof: "#1f3324", map: "#2a1116", try: "#4a2214" };
    const ids = Object.keys(tints).filter((k) => k !== "top");
    const pick = () => {
      let cur = "top";
      for (const id of ids) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top < innerHeight * .5) cur = id;
      }
      sky.style.setProperty("--tint", tints[cur]);
    };
    addEventListener("scroll", pick, { passive: true });
    pick();
  })();
})();
