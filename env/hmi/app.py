"""Read-only operator HMI: polls the ATV630 over Modbus/TCP and renders the live process."""

import os
import socket
import struct

from flask import Flask, jsonify, render_template

VFD_HOST = os.environ.get("VFD_HOST", "172.21.5.20")
VFD_PORT = int(os.environ.get("VFD_PORT", "502"))
UNIT_ID = 1

# Schneider ATV6xx logic addresses (see the VFD sim config)
REG = {
    "ETA": 3201, "RFR": 3202, "LCR": 3204, "OTR": 3205,
    "THR": 3207, "THD": 3211, "INLET": 5001,
    "CMD": 8501, "LFR": 8502, "RFRD": 8604,
}
WARN_C = 27.0
CRIT_C = 32.0
NOMINAL_HZ = 50.0

# ASCII fault-log block on the drive. Written by the VFD only once the cold aisle
# crosses thermal-critical, and cleared when it recovers (see env/vfd/atv630.py).
REG_FAULTLOG = 8800
FAULTLOG_COUNT = 48

app = Flask(__name__)


def decode_regs(words):
    """Decode holding registers packed 2 chars/reg big-endian, NUL-terminated."""
    raw = b"".join(struct.pack(">H", w & 0xFFFF) for w in words)
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace").strip()


def _read_holding(sock, addr, count, txid=1):
    pdu = struct.pack(">BHH", 0x03, addr, count)
    sock.sendall(struct.pack(">HHHB", txid, 0, len(pdu) + 1, UNIT_ID) + pdu)
    head = b""
    while len(head) < 7:
        c = sock.recv(7 - len(head))
        if not c:
            raise ConnectionError("closed")
        head += c
    length = struct.unpack(">HHHB", head)[2]
    body = b""
    while len(body) < length - 1:
        c = sock.recv((length - 1) - len(body))
        if not c:
            raise ConnectionError("closed")
        body += c
    if body[0] & 0x80:
        raise RuntimeError(f"modbus exc 0x{body[1]:02X}")
    n = body[1]
    return list(struct.unpack(f">{n // 2}H", body[2:2 + n]))


def poll():
    try:
        with socket.create_connection((VFD_HOST, VFD_PORT), timeout=2.0) as s:
            s.settimeout(2.0)
            b32 = _read_holding(s, 3201, 12)          # 3201..3212
            eta = b32[3201 - 3201]
            rfr = b32[3202 - 3201]
            lcr = b32[3204 - 3201]
            otr = b32[3205 - 3201]
            thr = b32[3207 - 3201]
            uop = b32[3208 - 3201]
            uln = b32[3209 - 3201]
            thd = b32[3211 - 3201]
            inlet = _read_holding(s, REG["INLET"], 1, 2)[0]
            cmd = _read_holding(s, REG["CMD"], 2, 3)
            rfrd = _read_holding(s, REG["RFRD"], 1, 4)[0]
            # Active fault string. Empty until a thermal-critical trip populates it;
            # isolated so a read hiccup here never knocks the whole page offline.
            try:
                faultlog_regs = _read_holding(s, REG_FAULTLOG, FAULTLOG_COUNT, 5)
            except Exception:
                faultlog_regs = []
    except Exception as e:
        return {"online": False, "error": str(e)}

    fault_log = decode_regs(faultlog_regs)

    temp_c = inlet / 10.0
    out_hz = rfr / 10.0
    ref_hz = cmd[1] / 10.0
    running = (cmd[0] & 0x000F) == 0x000F
    faulted = bool(eta & 0x0008)
    airflow = max(0.0, min(100.0, out_hz / NOMINAL_HZ * 100.0))

    if temp_c >= CRIT_C:
        state = "CRITICAL"
    elif temp_c >= WARN_C:
        state = "WARNING"
    else:
        state = "NORMAL"

    return {
        "online": True,
        "state": state,
        "temp_c": round(temp_c, 1),
        "setpoint_c": 21.0,
        "warn_c": WARN_C,
        "crit_c": CRIT_C,
        "out_hz": round(out_hz, 1),
        "ref_hz": round(ref_hz, 1),
        "rpm": rfrd,
        "current_a": round(lcr / 10.0, 1),
        "torque_pct": round(otr / 10.0, 1),
        "motor_thermal_pct": thr,
        "drive_thermal_pct": thd,
        "mains_v": uln,
        "motor_v": uop,
        "airflow_pct": round(airflow, 0),
        "running": running,
        "faulted": faulted,
        "eta_hex": f"0x{eta:04X}",
        "fault_log": fault_log,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    return jsonify(poll())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
