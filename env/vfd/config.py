"""Config for the simulated ATV630: register map, identity, thresholds, flags."""

# ---------------------------------------------------------------------------
# Modbus server
# ---------------------------------------------------------------------------
import os

MODBUS_HOST = os.environ.get("MODBUS_HOST", "0.0.0.0")
# In the container this is 502 (root). Overridable for unprivileged local tests.
MODBUS_PORT = int(os.environ.get("MODBUS_PORT", "502"))
UNIT_ID = 1                       # single slave; pymodbus single=True
MAX_ADDRESS = 8899                # size of the holding-register space we back

TICK_SECONDS = 1.0                # physics + telemetry update period

# ---------------------------------------------------------------------------
# Schneider ATV6xx register map (holding registers, function code 3 / 6 / 16)
# Addresses are decimal Schneider logic addresses.
# ---------------------------------------------------------------------------
# --- Command / reference ---
REG_CMD   = 8501   # CMD   Command word (CiA402 control word)         R/W
REG_LFR   = 8502   # LFR   Reference frequency, unit 0.1 Hz (signed)  R/W
REG_LFRD  = 8602   # LFRD  Speed setpoint, unit rpm                   R/W  (secondary, legit)

# --- Monitoring (read-only telemetry) ---
REG_ETA   = 3201   # ETA   Drive status word (CiA402 status word)     R
REG_RFR   = 3202   # RFR   Output (motor) frequency, unit 0.1 Hz      R
REG_RFRD  = 8604   # RFRD  Actual motor speed, unit rpm               R
REG_LCR   = 3204   # LCR   Motor current, unit 0.1 A                  R
REG_OTR   = 3205   # OTR   Motor torque, unit 0.1 %                   R

# --- Additional monitoring parameters ---
REG_THR   = 3207   # THR   Motor thermal state, unit %                R
REG_UOP   = 3208   # UOP   Motor voltage, unit V                      R
REG_ULN   = 3209   # ULN   Mains (line) voltage, unit V               R
REG_THD   = 3211   # THD   Drive thermal state, unit %                R

# Process tag: cooling-loop inlet temp mapped into a spare register, 0.1 C (non-OEM).
REG_INLET_TEMP = 5001

# --- Engineering "asset tag" nameplate block ---
REG_ASSET_BASE = 8700   # ASCII nameplate note, 2 chars/register

# --- Fault-log block (populated ONLY after a thermal-critical event) ---
REG_FAULTLOG_BASE = 8800  # ASCII fault record

# ---------------------------------------------------------------------------
# CiA402 control / status words (simplified but standards-shaped)
# ---------------------------------------------------------------------------
CMD_RUN            = 0x000F   # "Enable operation" -> motor runs
CMD_STOP           = 0x0006   # "Shutdown"         -> motor stops
ETA_RUNNING        = 0x0637   # Operation enabled
ETA_READY_STOPPED  = 0x0221   # Ready to switch on / stopped
ETA_FAULT_BIT      = 0x0008   # OR'd in when the drive flags a fault
ETA_FAULT          = ETA_FAULT_BIT | 0x0010 | 0x0020 | 0x0200  # 0x0238 Fault state: fault(3)+voltage-enabled(4)+quick-stop(5)+remote(9); OE/run/RTS dropped

# ---------------------------------------------------------------------------
# Process / thermal model (see atv630.py step_physics)
# ---------------------------------------------------------------------------
NOMINAL_HZ    = 50.0     # full-speed reference (LFR = 500 in 0.1 Hz units)
RAMP_HZ_PER_S = 10.0     # accel/decel limit -> ~5 s to spin down from 50 Hz
MOTOR_RPM_MAX = 1500     # 4-pole motor at 50 Hz

AMBIENT_COLD  = 21.0     # equilibrium inlet temp at full airflow (deg C)
AMBIENT_HOT   = 38.0     # equilibrium inlet temp at zero airflow (deg C)
TEMP_RATE     = 0.06     # first-order approach rate per tick (~20s to CRIT)

SETPOINT_C    = 21.0
WARN_C        = 27.0
CRIT_C        = 32.0

# ---------------------------------------------------------------------------
# FC43 (MEI 14) device identity
# ---------------------------------------------------------------------------
IDENTITY = {
    "VendorName": "Schneider Electric",
    "ProductCode": "ATV630",
    "MajorMinorRevision": "V3.3IE28",
    "VendorUrl": "http://www.schneider-electric.com",
    "ProductName": "Altivar Process ATV630",
    "ModelName": "ATV630D11N4",          # 11 kW / 400 V drive
    "UserApplicationName": "DC-COOL-VFD-01",
}
IDENTITY_PRIVATE_OBJECT = 0x80

def _t(h, k=b"MW-ENG-01/DC-EAST"):
    b = bytes.fromhex(h)
    return bytes(c ^ k[i % len(k)] for i, c in enumerate(b)).decode()


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------
FLAG_IDENTITY = _t("0b1b6c0235067966071c741c60750511011e081c0111016e040252")
FLAG_REGSWEEP = _t("0b1b6c0235146e787f1c750768171e01670a087e127d747d4d")
FLAG_IMPACT   = _t("0b1b6c0235041d007d660a04720e0f631706131d1200186c646719777350")
