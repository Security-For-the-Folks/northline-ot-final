#!/usr/bin/env python3
import os
import html
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.environ.get("PORTAL_ROOT", "/opt/portal")
MANUALS = os.path.join(BASE, "manuals")
BIND = os.environ.get("PORTAL_BIND", "0.0.0.0")
PORT = int(os.environ.get("PORTAL_PORT", "80"))

SITE = "DC-EAST"
NODE = "MW-ENG-01"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Site Maintenance Portal - {site}</title>
<style>
body{{font:14px/1.5 Tahoma,Geneva,sans-serif;color:#1b1b1b;background:#eef0f2;margin:0}}
.top{{background:#3a4a5a;color:#fff;padding:10px 18px;border-bottom:3px solid #d08a1d}}
.top b{{font-size:16px}} .top span{{color:#c7d2dd;font-size:12px}}
.wrap{{max-width:760px;margin:22px auto;background:#fff;border:1px solid #c3c9cf;padding:0 22px 18px}}
h2{{font-size:14px;color:#3a4a5a;border-bottom:1px solid #e2e5e8;padding-bottom:6px;margin-top:20px}}
ul{{list-style:none;padding:0}} li{{padding:5px 0;border-bottom:1px dotted #e2e5e8}}
a{{color:#1d5a8a;text-decoration:none}} a:hover{{text-decoration:underline}}
.meta{{color:#77808a;font-size:12px}} pre{{background:#f6f7f8;border:1px solid #d7dbdf;padding:12px;overflow:auto}}
.foot{{color:#8a9299;font-size:11px;margin-top:20px}}
</style></head><body>
<div class="top"><b>Site Maintenance Portal</b> &nbsp; <span>{site} / node {node}</span></div>
<div class="wrap">{body}
<div class="foot">Internal use only. For access issues contact the controls integrator.<br>
portal-svc build 4.2.1 &middot; do not expose to the enterprise network</div>
</div></body></html>"""


def render_index():
    try:
        docs = sorted(f for f in os.listdir(MANUALS) if not f.startswith("."))
    except OSError:
        docs = []
    items = "".join(
        '<li><a href="/manual?doc={q}">{n}</a> <span class="meta">document</span></li>'.format(
            q=urllib.parse.quote(d), n=html.escape(d))
        for d in docs)
    body = ("<h2>Maintenance documents</h2>"
            "<p class=\"meta\">Reference material left by the commissioning contractor "
            "for the cooling and drive systems on this node.</p>"
            "<ul>{items}</ul>").format(items=items or "<li class='meta'>none</li>")
    return PAGE.format(site=SITE, node=NODE, body=body)


def render_doc(doc):
    path = os.path.join(MANUALS, doc)
    with open(path, "rb") as fh:
        data = fh.read()
    text = data.decode("utf-8", "replace")
    body = ('<h2>{title}</h2><p><a href="/">&larr; back to documents</a></p><pre>{content}</pre>'
            .format(title=html.escape(doc), content=html.escape(text)))
    return PAGE.format(site=SITE, node=NODE, body=body)


class Handler(BaseHTTPRequestHandler):
    server_version = "portal-svc/4.2.1"

    def _send(self, code, page):
        raw = page.encode("utf-8", "replace")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        if parts.path == "/":
            self._send(200, render_index())
            return
        if parts.path == "/manual":
            q = urllib.parse.parse_qs(parts.query)
            doc = q.get("doc", [""])[0]
            if not doc:
                self._send(200, render_index())
                return
            try:
                self._send(200, render_doc(doc))
            except (OSError, ValueError):
                self._send(404, PAGE.format(site=SITE, node=NODE,
                           body="<h2>Not found</h2><p class='meta'>No such document.</p>"))
            return
        self._send(404, PAGE.format(site=SITE, node=NODE,
                   body="<h2>Not found</h2>"))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
