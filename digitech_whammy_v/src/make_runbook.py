"""Render the Whammy V measurement runbook as metrics.html.

The questionnaire itself lives in ``cfg/runbook.json`` - it is data, not code, so adding
a field is a one-line edit there and this renderer never changes. This script only turns
that file plus the manual's Page 2 views into one self-contained HTML page: reference
images inlined, entries kept in localStorage, everything exportable as JSON to be dropped
straight back into the config.

The manual's Page 2 drawing is the best available source of *topology* - what sits where,
and on which face - but its printed proportions are deliberately compressed, so none of
its dimensions can be trusted. The runbook therefore asks for the scale from calipers and
uses the drawing only to say where each measurement belongs.

    .venv/Scripts/python digitech_whammy_v/src/make_runbook.py
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
REF = PROJECT / "ref"
SPEC = PROJECT / "cfg" / "runbook.json"
OUT = PROJECT / "metrics.html"

GLYPHS = {
    "x": '<path d="M8 32 H52"/><path d="M8 26 v12 M52 26 v12"/>'
         '<text x="30" y="22" text-anchor="middle">X</text>',
    "y": '<path d="M30 8 V52"/><path d="M24 8 h12 M24 52 h12"/>'
         '<text x="42" y="34">Y</text>',
    "z": '<path d="M30 52 V8"/><path d="M24 52 h12 M24 8 h12"/>'
         '<text x="42" y="34">Z</text>',
    "dia": '<circle cx="30" cy="30" r="14" fill="none"/>'
           '<path d="M16 30 H44"/><path d="M16 25 v10 M44 25 v10"/>'
           '<text x="52" y="34">&#8960;</text>',
    "pos": '<rect x="10" y="12" width="40" height="40" fill="none" stroke="#bbb"/>'
           '<circle cx="34" cy="26" r="3" class="pt"/>'
           '<path d="M10 40 H34" stroke-dasharray="3 2"/>'
           '<path d="M34 52 V26" stroke-dasharray="3 2"/>',
    "count": '<text x="30" y="40" text-anchor="middle" font-size="26">#</text>',
    "yesno": '<text x="30" y="40" text-anchor="middle" font-size="26">?</text>',
    "text": '<text x="30" y="40" text-anchor="middle" font-size="26">A</text>',
}

NUMERIC = {"x", "y", "z", "dia"}

PRIO = {1: ("must", "p1"), 2: ("helpful", "p2"), 3: ("optional", "p3")}


def inline(path: Path, width: int, quality: int = 82) -> str:
    """Read an image, cap its width, and return it as a data URI."""
    image = Image.open(path).convert("RGB")
    if image.width > width:
        height = round(image.height * width / image.width)
        image = image.resize((width, height), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def glyph(kind: str) -> str:
    return f'<svg class="g" viewBox="0 0 60 60" aria-hidden="true">{GLYPHS[kind]}</svg>'


def metric_row(metric: dict) -> str:
    kind = metric["glyph"]
    label, css = PRIO[metric["priority"]]
    numeric = kind in NUMERIC
    placeholder = metric["hint"] or ("mm" if numeric else "")
    input_type = "number" if numeric else "text"
    step = ' step="0.01"' if numeric else ""
    mode = "decimal" if numeric else "text"
    return f"""
      <tr data-id="{metric['id']}">
        <td class="gid">{metric['id']}</td>
        <td class="gl">{glyph(kind)}</td>
        <td class="what">
          <label for="v_{metric['id']}">{metric['label']}</label>
          <span class="prio {css}">{label}</span>
          <p class="how">{metric['how']}</p>
        </td>
        <td class="inp">
          <input id="v_{metric['id']}" data-id="{metric['id']}" type="{input_type}"{step}
                 inputmode="{mode}" placeholder="{placeholder}">
          <input class="note" data-note="{metric['id']}" type="text"
                 placeholder="note (optional)">
        </td>
      </tr>"""


def section_html(section: dict) -> str:
    figure = ""
    if "image" in section:
        image = section["image"]
        src = inline(REF / "manual" / image["file"], image["width"])
        figure = (f'<figure><img src="{src}" alt="{image["caption"]}">'
                  f'<figcaption>{image["caption"]}</figcaption></figure>')
    rows = "".join(metric_row(metric) for metric in section["metrics"])
    return f"""
  <section id="{section['id']}">
    <h2>{section['title']}</h2>
    <p class="intro">{section['intro']}</p>
    {figure}
    <table class="m">
      <thead><tr><th>ID</th><th></th><th>What to measure</th><th>Your reading</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>"""


CSS = """
:root{--ink:#1a1a1a;--dim:#5f6b7a;--line:#dfe4ea;--accent:#1e6b4f;--warn:#8a7431}
*{box-sizing:border-box}
body{margin:0;background:#f4f6f8;color:var(--ink);
 font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header{position:sticky;top:0;z-index:9;background:#fff;border-bottom:1px solid var(--line);
 padding:14px 22px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
header h1{font-size:17px;margin:0;font-weight:650}
header .sub{color:var(--dim);font-size:13px}
.bar{flex:1;min-width:160px;height:8px;background:var(--line);border-radius:4px;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:var(--accent);transition:width .2s}
button{font:inherit;font-size:13px;padding:7px 13px;border-radius:7px;cursor:pointer;
 border:1px solid var(--line);background:#fff;color:var(--ink)}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
button:hover{border-color:#b9c2cc}
main{max-width:1080px;margin:0 auto;padding:22px 22px 150px}
section{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px 22px;
 margin-bottom:20px}
h2{font-size:16px;margin:0 0 6px}
.intro{color:#33404e;margin:0 0 14px;font-size:14px}
figure{margin:0 0 16px;background:#fbfcfd;border:1px solid var(--line);border-radius:9px;
 padding:10px;overflow:auto}
figure img{display:block;max-width:100%;height:auto}
figcaption{color:var(--dim);font-size:12px;margin-top:7px}
table.m{width:100%;border-collapse:collapse}
table.m th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--dim);font-weight:600;padding:0 8px 7px;border-bottom:1px solid var(--line)}
table.m td{vertical-align:top;padding:11px 8px;border-bottom:1px solid #eef1f4}
table.m tr:last-child td{border-bottom:0}
.gid{width:44px;font:600 13px ui-monospace,Menlo,Consolas,monospace;color:var(--accent)}
.gl{width:52px}
svg.g{width:42px;height:42px}
svg.g path,svg.g circle,svg.g rect{fill:none;stroke:#c0392b;stroke-width:1.6}
svg.g .pt{fill:#c0392b;stroke:none}
svg.g rect{stroke:#bbb}
svg.g text{font:11px sans-serif;fill:#555;stroke:none}
.what{min-width:340px}
.what label{font-weight:600;font-size:14px}
.how{margin:3px 0 0;color:#4a5764;font-size:13px}
.prio{font-size:10px;text-transform:uppercase;letter-spacing:.05em;padding:2px 6px;
 border-radius:20px;margin-left:6px;vertical-align:2px;font-weight:700}
.p1{background:#e8f3ee;color:#1e6b4f}
.p2{background:#eef2f7;color:#5f6b7a}
.p3{background:#f6f2e8;color:var(--warn)}
.inp{width:200px}
.inp input{width:100%;font:inherit;font-size:14px;padding:8px 10px;border-radius:7px;
 border:1px solid #ccd3db;background:#fff}
.inp input:focus{outline:2px solid #b7d8ca;border-color:var(--accent)}
.inp input.filled{background:#f3faf7;border-color:#a8cfbe}
.inp input.note{margin-top:6px;font-size:12.5px;padding:6px 10px;background:#fcfdfe}
footer{max-width:1080px;margin:0 auto 46px;padding:0 22px;color:var(--dim);font-size:13px}
.tray{position:fixed;right:14px;bottom:14px;background:#fff;border:1px solid var(--line);
 border-radius:11px;padding:8px 11px;box-shadow:0 4px 18px rgba(20,30,40,.13);
 display:flex;flex-direction:column;gap:7px;width:auto;max-width:250px}
.tray button.tog{font-size:12px;font-weight:600;color:var(--dim);border:0;background:none;
 padding:0;text-align:left;display:flex;gap:6px;align-items:center}
.tray .body{display:none;flex-direction:column;gap:7px;width:236px}
.tray.open .body{display:flex}
.tray textarea{width:100%;height:120px;font:10.5px ui-monospace,Menlo,Consolas,monospace;
 border:1px solid var(--line);border-radius:6px;padding:6px;resize:vertical}
@media (max-width:820px){
 .what{min-width:0}
 table.m,table.m tbody,table.m tr,table.m td{display:block}
 table.m thead{display:none}
 table.m tr{display:grid;grid-template-columns:44px 52px 1fr;gap:0 8px;
  padding:12px 0;border-bottom:1px solid #eef1f4}
 table.m td{border:0;padding:0}
 table.m td.inp{grid-column:2 / -1;width:auto;margin-top:10px}
}
@media print{header,.tray{display:none}body{background:#fff}section{break-inside:avoid}}
"""

JS = r"""
const KEY = 'whammy-runbook-v1';
const state = JSON.parse(localStorage.getItem(KEY) || '{}');

function save() {
  document.querySelectorAll('input[data-id]').forEach(el => {
    const id = el.dataset.id;
    const note = el.closest('td').querySelector('.note').value;
    const value = el.value.trim();
    el.classList.toggle('filled', value !== '');
    if (value === '' && note.trim() === '') delete state[id];
    else state[id] = { v: value, n: note };
  });
  localStorage.setItem(KEY, JSON.stringify(state));
  progress();
}

function progress() {
  let done = 0, must = 0, mustDone = 0;
  document.querySelectorAll('tr[data-id]').forEach(tr => {
    const el = tr.querySelector('input[data-id]');
    const isMust = !!tr.querySelector('.p1');
    const ok = el.value.trim() !== '';
    if (ok) done++;
    if (isMust) { must++; if (ok) mustDone++; }
  });
  const total = document.querySelectorAll('tr[data-id]').length;
  document.querySelector('.bar i').style.width = (100 * done / total) + '%';
  document.querySelector('.sub').textContent =
    done + ' of ' + total + ' filled \u00b7 ' + mustDone + ' of ' + must + ' essentials';
}

function payload() {
  const out = {
    schema_version: 1,
    device: 'DigiTech Whammy V',
    units: 'mm',
    recorded: new Date().toISOString(),
    readings: {}
  };
  document.querySelectorAll('input[data-id]').forEach(el => {
    const value = el.value.trim();
    const note = el.closest('td').querySelector('.note').value.trim();
    if (value === '' && note === '') return;
    const n = Number(value);
    out.readings[el.dataset.id] = {
      value: (value !== '' && !isNaN(n)) ? n : value,
      note: note
    };
  });
  return out;
}

function copyJSON() {
  const text = JSON.stringify(payload(), null, 2);
  document.querySelector('.tray textarea').value = text;
  toggleTray(true);
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(
      () => flash('Copied \u2014 paste it back to me'),
      () => { document.querySelector('.tray textarea').select(); flash('Select-all and copy'); }
    );
  } else {
    document.querySelector('.tray textarea').select();
    flash('Select-all and copy');
  }
}

function saveJSON() {
  const blob = new Blob([JSON.stringify(payload(), null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'whammy-metrics.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

function toggleTray(force) {
  const tray = document.getElementById('tray');
  const open = (force === undefined) ? !tray.classList.contains('open') : force;
  tray.classList.toggle('open', open);
  document.getElementById('trayIcon').innerHTML = open ? '&#9662;' : '&#9656;';
}

function flash(message) {
  const el = document.querySelector('.tray .msg');
  el.textContent = message;
  el.style.opacity = 1;
  setTimeout(() => { el.style.opacity = 0; }, 2200);
}

function clearAll() {
  if (!confirm('Clear every reading?')) return;
  localStorage.removeItem(KEY);
  document.querySelectorAll('input').forEach(el => { el.value = ''; });
  document.querySelectorAll('input[data-id]').forEach(el => el.classList.remove('filled'));
  document.querySelectorAll('tr[data-id]').forEach(tr => { delete state[tr.dataset.id]; });
  progress();
}

document.querySelectorAll('input[data-id]').forEach(el => {
  const id = el.dataset.id;
  const td = el.closest('td');
  if (state[id]) {
    el.value = state[id].v || '';
    td.querySelector('.note').value = state[id].n || '';
    el.classList.toggle('filled', el.value.trim() !== '');
  }
  el.addEventListener('input', save);
});
document.querySelectorAll('input[data-note]').forEach(el => el.addEventListener('input', save));
progress();
"""

PREAMBLE = """
  <section>
    <h2>How to use this sheet</h2>
    <p class="intro">
      Every field wants <b>millimetres</b>, to 0.1 mm. Use the calipers' jaws for outside
      and inside spans, and the depth rod for heights. Where a number is awkward to reach,
      put your best reading in the value box and say why in the note - a flagged
      approximation is far more use to me than a blank.
    </p>
    <p class="intro">
      <b>Why this exists.</b> The manual's Page 2 drawing is the right <i>shape</i>, but its
      printed proportions are deliberately compressed, so none of its dimensions can be
      trusted. The drawing tells me <i>where</i> a feature is and on which face; only your
      calipers can tell me <i>how big</i> it is. Nothing in the model will be copied from
      the manual.
    </p>
    <p class="intro">
      <b>Two photographs are worth ten numbers.</b> The top face shot square-on from
      directly above with a steel rule lying on it; and one long side shot square-on with
      the rule along it. Send those and I can cross-check every reading against them.
    </p>
    <p class="intro" style="margin-bottom:0">
      Entries save in this browser as you type. <b>Copy JSON</b> puts the whole set on the
      clipboard - paste it back and I will build the config from it.
    </p>
  </section>
"""


def build() -> Path:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    body = "".join(section_html(section) for section in spec["sections"])
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Whammy V \u2014 measurement runbook</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <div>
    <h1>Whammy V \u2014 measurement runbook</h1>
    <div class="sub">loading\u2026</div>
  </div>
  <div class="bar"><i></i></div>
  <button class="primary" onclick="copyJSON()">Copy JSON</button>
  <button onclick="saveJSON()">Save .json</button>
  <button onclick="clearAll()">Clear</button>
</header>

<main>
{PREAMBLE}
{body}
</main>

<footer>
  Reference views: DigiTech Whammy V owner's manual, Page 2 \u201cGuided Tour \u2014
  Detailed Description\u201d, extracted at 1200 dpi. Use them to locate a feature, never
  to scale it.
</footer>

<div class="tray" id="tray">
  <button class="tog" onclick="toggleTray()">
    <span id="trayIcon">&#9656;</span> Export JSON
  </button>
  <div class="body">
    <textarea readonly placeholder="Copy JSON fills this box"></textarea>
    <div class="msg" style="font-size:12px;color:var(--accent);opacity:0;
         transition:opacity .3s;min-height:16px"></div>
  </div>
</div>

<script>{JS}</script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    total = sum(len(s["metrics"]) for s in spec["sections"])
    must = sum(1 for s in spec["sections"] for m in s["metrics"] if m["priority"] == 1)
    print(f"wrote {OUT.relative_to(PROJECT)}  ({OUT.stat().st_size / 1024:.0f} kB)")
    print(f"  {len(spec['sections'])} sections, {total} fields, {must} essentials")
    return OUT


if __name__ == "__main__":
    build()
