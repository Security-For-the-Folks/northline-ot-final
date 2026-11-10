#!/usr/bin/env python3
"""Row A Process Historian - lightweight trend-reporting front end (SQLite-backed).

A small internal reporting page an operator uses to pull historical trends for a
plant asset tag. This models the "soft SQL underbelly" of an OT cell: the drive
and HMI speak Modbus, but the historian that logs them is a database with a thin
web report on top.

The tag lookup builds its SQL by string concatenation, so the `tag` parameter is
injectable. The page returns only a boolean-style result (samples on record vs.
none) -- there is no reflected row data -- so pulling the engineering notes out
by hand is impractical; an automated blind-injection tool is the realistic way.

Runs fully offline. The database is seeded on first start; no network fetches.
"""
import os
import html
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _t(h, k=b"MW-ENG-01/DC-EAST"):
    b = bytes.fromhex(h)
    return bytes(c ^ k[i % len(k)] for i, c in enumerate(b)).decode()

DB = os.environ.get("HIST_DB", "/opt/historian/historian.db")
BIND = os.environ.get("HIST_BIND", "0.0.0.0")
PORT = int(os.environ.get("HIST_PORT", "80"))

SITE = "DC-EAST"
NODE = "MW-HIST-01"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Row A Process Historian - {site}</title>
<style>
body{{font:14px/1.5 Tahoma,Geneva,sans-serif;color:#161d24;background:#e9edf1;margin:0}}
.top{{background:#22333f;color:#fff;padding:10px 18px;border-bottom:3px solid #2e8b8b}}
.top b{{font-size:16px}} .top span{{color:#b9c7d1;font-size:12px}}
.wrap{{max-width:780px;margin:22px auto;background:#fff;border:1px solid #c3c9cf;padding:0 22px 18px}}
h2{{font-size:14px;color:#22333f;border-bottom:1px solid #e2e5e8;padding-bottom:6px;margin-top:20px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{text-align:left;padding:4px 8px;border-bottom:1px solid #eceff1}}
th{{color:#5b6670;font-weight:600}}
form{{margin:12px 0}} input[type=text]{{padding:5px 7px;border:1px solid #b7bfc6;width:260px}}
button{{padding:5px 12px;background:#2e8b8b;color:#fff;border:0;cursor:pointer}}
.ok{{color:#1c6b2b}} .empty{{color:#8a5a00}}
.meta{{color:#77808a;font-size:12px}} .foot{{color:#8a9299;font-size:11px;margin-top:20px}}
code{{background:#f2f4f6;padding:1px 4px;border:1px solid #e0e4e8}}
</style></head><body>
<div class="top"><b>Row A Process Historian</b> &nbsp; <span>{site} / node {node}</span></div>
<div class="wrap">{body}
<div class="foot">Internal reporting only. Tag data retained per DC-EAST data policy.<br>
historian-report svc 2.3 &middot; not for enterprise exposure</div>
</div></body></html>"""


def _connect():
    con = sqlite3.connect(DB)
    return con


def seed():
    """Create and populate the historian DB if it does not exist yet."""
    if os.path.exists(DB):
        return
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = _connect()
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE assets(
            asset_tag TEXT PRIMARY KEY,
            description TEXT,
            area TEXT,
            unit TEXT
        );
        CREATE TABLE samples(
            id INTEGER PRIMARY KEY,
            asset_tag TEXT,
            ts TEXT,
            channel TEXT,
            value REAL
        );
        CREATE TABLE eng_notes(
            id INTEGER PRIMARY KEY,
            author TEXT,
            created TEXT,
            note TEXT
        );
        CREATE TABLE users(
            username TEXT PRIMARY KEY,
            pwhash TEXT,
            role TEXT
        );
        """
    )

    cur.executemany(
        "INSERT INTO assets(asset_tag,description,area,unit) VALUES(?,?,?,?)",
        [
            ("DC-COOL-VFD-01", "Row A cooling fan VFD (ATV630)", "Row A cold aisle", "Hz"),
            ("DC-COOL-CRAC-01", "Row A chilled-water CRAC unit", "Row A cold aisle", "degC"),
            ("DC-PWR-UPS-01", "Row A UPS branch", "Row A power", "V"),
        ],
    )

    # A believable slab of process history for the cooling fan and cold aisle.
    rows = []
    sid = 1
    for m in range(240):  # 240 minutes of one-minute samples
        hh = 2 + (m // 60)
        mm = m % 60
        ts = "2026-09-10T%02d:%02d:00" % (hh, mm)
        # fan holds ~50 Hz; cold aisle holds ~21 C with mild drift
        hz = 50.0 + ((m % 7) - 3) * 0.1
        temp = 21.0 + ((m % 11) - 5) * 0.05
        rows.append((sid, "DC-COOL-VFD-01", ts, "OUT_HZ", round(hz, 2))); sid += 1
        rows.append((sid, "DC-COOL-CRAC-01", ts, "INLET_C", round(temp, 2))); sid += 1
    cur.executemany(
        "INSERT INTO samples(id,asset_tag,ts,channel,value) VALUES(?,?,?,?,?)", rows
    )

    cur.executemany(
        "INSERT INTO eng_notes(id,author,created,note) VALUES(?,?,?,?)",
        [
            (1, "integrator",  "2026-08-14",
             "Row A cooling VFD (DC-COOL-VFD-01) commissioned. Baseline 50.0 Hz, "
             "cold aisle 21 C. Historian polling asset every 60 s."),
            (2, "integrator",  "2026-08-27",
             "Intermittent overnight high-temp trips logged on Row A (see WO DC-1471). "
             "No stored drive hardware fault; cause not identified."),
            (3, "integrator",  "2026-08-31",
             "COMMISSIONING HANDOVER (WO DC-1471). Row A cooling fan VFD "
             "DC-COOL-VFD-01 at 172.21.5.20 is driven over Modbus/TCP holding "
             "registers: command word CMD = reg 8501 (0x000F run, 0x0006 stop); "
             "speed reference LFR = reg 8502 in 0.1 Hz (500 = 50.0 Hz normal). "
             "Overnight high-temp trips traced to LFR (8502) being forced to 0 from "
             "an unauthorized host -- fan stops, cold aisle climbs. Handover token "
             + _t("0b1b6c02350f1c63651f1672190b1e00050166727616011c7c4c") + ". Rotate the historian svc account and scope "
             "Modbus writes to the drive before go-live."),
            (4, "night-shift", "2026-09-02",
             "Temporary night-shift reporting login left active on this historian; "
             "flagged for removal at handover."),
        ],
    )

    cur.executemany(
        "INSERT INTO users(username,pwhash,role) VALUES(?,?,?)",
        [
            ("hist_svc",  "$apr1$qN8s2H1a$m0Xr3s2u9Lq0pB7aQ1c9x/", "service"),
            ("report_ro", "$apr1$r4Tq7bY2$eE1lJk8sQ2mV0nZ7pR3d5.", "readonly"),
            ("nightshift","$apr1$Zc5m1oP0$aA2bC3dD4eE5fF6gG7hH8/", "readonly"),
        ],
    )

    con.commit()
    con.close()


def render_index():
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT asset_tag,description,area FROM assets ORDER BY asset_tag")
    assets = cur.fetchall()
    con.close()
    rows = "".join(
        "<tr><td><code>{t}</code></td><td>{d}</td><td>{a}</td></tr>".format(
            t=html.escape(t), d=html.escape(d), a=html.escape(a))
        for (t, d, a) in assets)
    body = (
        "<h2>Trend report</h2>"
        "<p class=\"meta\">Pull recorded trend samples for a plant asset tag. "
        "Reporting front end for the Row A process historian.</p>"
        "<form action=\"/trend\" method=\"get\">"
        "<input type=\"text\" name=\"tag\" placeholder=\"asset tag\" value=\"DC-COOL-VFD-01\">"
        "<button type=\"submit\">Report</button></form>"
        "<h2>Known asset tags</h2>"
        "<table><tr><th>Asset tag</th><th>Description</th><th>Area</th></tr>"
        "{rows}</table>").format(rows=rows)
    return PAGE.format(site=SITE, node=NODE, body=body)


def render_trend(tag):
    """Look up whether the asset tag has recorded samples.

    VULNERABLE BY DESIGN: `tag` is concatenated straight into the SQL. The page
    exposes only a boolean-style result, which makes this a blind-injection
    oracle rather than a data-reflecting one.
    """
    con = _connect()
    cur = con.cursor()
    sql = "SELECT COUNT(*) FROM samples WHERE asset_tag = '%s'" % tag
    try:
        cur.execute(sql)
        n = cur.fetchone()[0]
    except Exception:
        # A syntactically broken injection reads as "no data" -> stable false branch.
        n = 0
    con.close()

    safe_tag = html.escape(tag)
    if n and n > 0:
        body = (
            "<h2>Trend report</h2>"
            "<p><a href=\"/\">&larr; back</a></p>"
            "<p id=\"result-ok\" class=\"ok\">Samples on record for this asset tag. "
            "Trend available in the operator client.</p>"
            "<p class=\"meta\">Query: <code>{t}</code></p>").format(t=safe_tag)
    else:
        body = (
            "<h2>Trend report</h2>"
            "<p><a href=\"/\">&larr; back</a></p>"
            "<p id=\"result-empty\" class=\"empty\">No samples on record for that "
            "asset tag.</p>"
            "<p class=\"meta\">Query: <code>{t}</code></p>").format(t=safe_tag)
    return PAGE.format(site=SITE, node=NODE, body=body)


class Handler(BaseHTTPRequestHandler):
    server_version = "historian-report/2.3"

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
        if parts.path == "/trend":
            q = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
            tag = q.get("tag", [""])[0]
            if not tag:
                self._send(200, render_index())
                return
            self._send(200, render_trend(tag))
            return
        self._send(404, PAGE.format(site=SITE, node=NODE, body="<h2>Not found</h2>"))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    seed()
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
