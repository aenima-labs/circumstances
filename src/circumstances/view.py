"""Read-only local viewer for sealed run bundles."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from circumstances.bundles import compare_bundles, list_bundles, resolve_bundle, show_bundle
from circumstances.errors import CircumstancesError

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Circumstances</title>
<style>
  :root { color-scheme: light; }
  body { margin: 2rem auto; max-width: 960px; padding: 0 1rem;
    font: 15px/1.45 ui-sans-serif, system-ui, sans-serif; color: #1c1917; }
  h1 { font-size: 1.4rem; margin-bottom: 0.25rem; }
  h2 { font-size: 1.05rem; margin: 1.5rem 0 0.5rem; }
  p.note { color: #57534e; }
  button, select { font: inherit; }
  button { margin: 0 0.4rem 0.4rem 0; }
  table { border-collapse: collapse; width: 100%; }
  th, td { text-align: left; border-bottom: 1px solid #e7e5e4; padding: 0.35rem 0.4rem;
    vertical-align: top; }
  .fail { color: #9f1239; }
  .pass { color: #166534; }
  .warn { background: #fff7ed; border: 1px solid #fdba74; padding: 0.6rem 0.8rem; }
  pre { white-space: pre-wrap; font: 13px/1.4 ui-monospace, monospace; }
  .event { margin: 0.3rem 0; }
</style>
</head>
<body>
<h1>Circumstances</h1>
<p class="note">Read-only view of sealed bundles. This page does not start runs or edit packs.</p>
<div id="runs"></div>
<h2>Compare</h2>
<p>
  <select id="left"></select>
  <select id="right"></select>
  <button id="compare" type="button">Compare</button>
</p>
<div id="comparison"></div>
<div id="detail"></div>
<script>
const runs = document.querySelector("#runs");
const left = document.querySelector("#left");
const right = document.querySelector("#right");
const comparison = document.querySelector("#comparison");
const detail = document.querySelector("#detail");

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function repetition(value) {
  if (!value) return "";
  return value.trials + " trials · pass@" + value.k + " " +
    Number(value.pass_at_k).toFixed(2) + " · pass^" + value.k + " " +
    Number(value.pass_hat_k).toFixed(2);
}

async function loadRuns() {
  const response = await fetch("/api/runs");
  const payload = await response.json();
  runs.replaceChildren();
  left.replaceChildren();
  right.replaceChildren();
  if (!payload.runs.length) {
    runs.append(el("p", "No sealed bundles in this results directory.", "note"));
    return;
  }
  for (const run of payload.runs) {
    const button = el("button", run.run_id + " · " + run.pack_id + " · " +
      (run.passed ? "pass" : "fail"));
    button.type = "button";
    button.addEventListener("click", () => loadRun(run.run_id));
    runs.append(button);
    for (const select of [left, right]) {
      const option = el("option", run.run_id);
      option.value = run.run_id;
      select.append(option);
    }
  }
}

async function loadRun(id) {
  const response = await fetch("/api/runs/" + encodeURIComponent(id));
  const run = await response.json();
  detail.replaceChildren(el("h2", run.pack_id + " · " + run.run_id));
  const groups = new Map();
  for (const item of run.cases) {
    if (!groups.has(item.rule_id)) groups.set(item.rule_id, []);
    groups.get(item.rule_id).push(item);
  }
  for (const [rule, cases] of groups) {
    detail.append(el("h2", rule));
    for (const item of cases) {
      const heading = el("p");
      heading.append(el("strong", item.case_id));
      heading.append(el("span", " · " + (item.passed ? "pass" : "fail") + " · " + repetition(item),
        item.passed ? "pass" : "fail"));
      detail.append(heading);
      for (const attempt of item.attempts) {
        detail.append(el("h2", "Trial " + attempt.attempt));
        for (const event of attempt.events) {
          const line = event.kind +
            (event.role ? " " + event.role : "") +
            (event.name ? " " + event.name : "") +
            (event.content ? ": " + event.content : "");
          detail.append(el("p", line, "event"));
        }
        for (const grade of attempt.grades) {
          detail.append(el("p", grade.evaluator_id + " · " + grade.tier + " · " + grade.status +
            (grade.reasoning ? " · " + grade.reasoning : ""),
            grade.status === "pass" ? "pass" : "fail"));
        }
      }
    }
  }
}

document.querySelector("#compare").addEventListener("click", async () => {
  const response = await fetch("/api/compare?a=" + encodeURIComponent(left.value) +
    "&b=" + encodeURIComponent(right.value));
  const payload = await response.json();
  comparison.replaceChildren();
  if (!response.ok) {
    comparison.append(el("p", payload.error || "Comparison refused.", "warn"));
    return;
  }
  const summary = payload.summary;
  comparison.append(el("p", "fixed " + summary.fixed + " · regressed " + summary.regressed +
    " · same " + summary.same + " · only A " + summary.only_a + " · only B " + summary.only_b));
  const table = document.createElement("table");
  const head = document.createElement("tr");
  for (const label of ["Case", "Change", "A", "B"]) head.append(el("th", label));
  table.append(head);
  for (const item of payload.cases) {
    const row = document.createElement("tr");
    row.append(el("td", item.case_id));
    row.append(el("td", item.change));
    row.append(el("td", repetition(item.a)));
    row.append(el("td", repetition(item.b)));
    table.append(row);
  }
  comparison.append(table);
});

loadRuns();
</script>
</body>
</html>
"""


def make_server(results: Path, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Build a local server. ``port=0`` asks the OS for a free port."""
    root = results.expanduser().resolve()
    handler = _handler(root)
    server = ThreadingHTTPServer((host, port), handler)
    return server


def serve(results: Path, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = make_server(results, host, port)
    bound = server.server_address
    shown_host = bound[0].decode() if isinstance(bound[0], bytes) else bound[0]
    print(f"http://{shown_host}:{bound[1]}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _handler(results: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                _send(self, 200, PAGE.encode(), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/runs":
                _send_json(self, 200, {"runs": list_bundles(results)})
                return
            if parsed.path.startswith("/api/runs/"):
                run_id = parsed.path.removeprefix("/api/runs/")
                try:
                    bundle = resolve_bundle(run_id, results)
                    _send_json(self, 200, show_bundle(bundle))
                except CircumstancesError as exc:
                    _send_json(self, 404, {"error": str(exc)})
                return
            if parsed.path == "/api/compare":
                query = parse_qs(parsed.query)
                left = query.get("a", [""])[0]
                right = query.get("b", [""])[0]
                if not left or not right:
                    _send_json(self, 400, {"error": "a and b run ids are required"})
                    return
                try:
                    payload = compare_bundles(
                        resolve_bundle(left, results),
                        resolve_bundle(right, results),
                    )
                except CircumstancesError as exc:
                    reasons = getattr(exc, "reasons", [str(exc)])
                    _send_json(self, 409, {"error": str(exc), "reasons": reasons})
                    return
                _send_json(self, 200, payload)
                return
            _send_json(self, 404, {"error": "not found"})

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    return Handler


def _send(handler: BaseHTTPRequestHandler, status: int, body: bytes, content_type: str) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: object) -> None:
    _send(handler, status, json.dumps(payload).encode(), "application/json")
