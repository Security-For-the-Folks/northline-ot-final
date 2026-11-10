"""Simulated Schneider ATV630 VFD over Modbus/TCP: speed -> airflow -> inlet temp."""

import logging
import threading
import time

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server.async_io import ModbusServerRequestHandler, StartTcpServer
from pymodbus.device import ModbusDeviceIdentification

import config as cfg

log = logging.getLogger("atv630")


# pymodbus 3.7.x leak fix. Each per-client handler is built with is_server=True,
# so when a client disconnects, connection_lost() "relistens": every closed Modbus
# connection leaves an extra listening socket on a random port (~12 KB each,
# never freed). Students saw RAM climb for hours and nmap showed hundreds of
# bogus open ports on the drive. is_server is only read at init (already done)
# and on close, so clearing it here gives the 3.8+ behaviour: close the
# connection, drop it from the listener's table, do not relisten.
# Remove this if pymodbus is upgraded to >=3.8 (fixed upstream via is_listener).
_handler_init = ModbusServerRequestHandler.__init__


def _client_handler_init(self, owner):
    _handler_init(self, owner)
    self.is_server = False


ModbusServerRequestHandler.__init__ = _client_handler_init


# zero_mode: wire address == block index (register N reads block[N]).
_hr = ModbusSequentialDataBlock(0, [0] * (cfg.MAX_ADDRESS + 1))
_slave = ModbusSlaveContext(hr=_hr, zero_mode=True)
context = ModbusServerContext(slaves=_slave, single=True)


def read_reg(addr: int) -> int:
    return _hr.getValues(addr, 1)[0]


def write_reg(addr: int, value: int) -> None:
    _hr.setValues(addr, [int(value) & 0xFFFF])


def write_ascii(base: int, text: str) -> None:
    # pack ASCII into holding registers, 2 chars/reg, big-endian, NUL-padded
    data = text.encode("ascii", "replace")
    if len(data) % 2:
        data += b"\x00"
    regs = [(data[i] << 8) | data[i + 1] for i in range(0, len(data), 2)]
    _hr.setValues(base, regs)


def clear_block(base: int, count: int) -> None:
    _hr.setValues(base, [0] * count)


# ---------------------------------------------------------------------------
# Identity (FC43 / MEI 14)
# ---------------------------------------------------------------------------
def build_identity() -> ModbusDeviceIdentification:
    ident = ModbusDeviceIdentification()
    ident.VendorName = cfg.IDENTITY["VendorName"]
    ident.ProductCode = cfg.IDENTITY["ProductCode"]
    ident.MajorMinorRevision = cfg.IDENTITY["MajorMinorRevision"]
    ident.VendorUrl = cfg.IDENTITY["VendorUrl"]
    ident.ProductName = cfg.IDENTITY["ProductName"]
    ident.ModelName = cfg.IDENTITY["ModelName"]
    ident.UserApplicationName = cfg.IDENTITY["UserApplicationName"]
    # Private/extended object -- only returned on an "extended" identity read.
    ident[cfg.IDENTITY_PRIVATE_OBJECT] = cfg.FLAG_IDENTITY
    return ident


# ---------------------------------------------------------------------------
# Initial register state (drive running at nominal speed = normal operation)
# ---------------------------------------------------------------------------
def seed_registers() -> None:
    write_reg(cfg.REG_CMD, cfg.CMD_RUN)
    write_reg(cfg.REG_LFR, int(cfg.NOMINAL_HZ * 10))      # 500 = 50.0 Hz
    write_reg(cfg.REG_LFRD, cfg.MOTOR_RPM_MAX)
    write_reg(cfg.REG_ETA, cfg.ETA_RUNNING)
    write_reg(cfg.REG_ULN, 400)
    # Engineering asset-tag nameplate block
    write_ascii(
        cfg.REG_ASSET_BASE,
        "ASSET DC-COOL-VFD-01 ATV630D11N4 SN:9G2148A00312 "
        + cfg.FLAG_REGSWEEP,
    )


# ---------------------------------------------------------------------------
# Physics: commanded speed -> airflow -> inlet temperature
# ---------------------------------------------------------------------------
class Plant:
    def __init__(self):
        self.actual_hz = cfg.NOMINAL_HZ
        self.inlet_temp = cfg.AMBIENT_COLD
        self.faulted = False
        self.impact_latched = False

    def step(self):
        cmd = read_reg(cfg.REG_CMD)
        lfr = read_reg(cfg.REG_LFR)                # 0.1 Hz, signed
        if lfr >= 0x8000:
            lfr -= 0x10000
        running = (cmd & 0x000F) == (cfg.CMD_RUN & 0x000F)
        target_hz = (lfr / 10.0) if running else 0.0
        target_hz = max(0.0, min(cfg.NOMINAL_HZ, target_hz))

        # Ramp actual speed toward target (accel/decel limited)
        step_limit = cfg.RAMP_HZ_PER_S * cfg.TICK_SECONDS
        delta = target_hz - self.actual_hz
        self.actual_hz += max(-step_limit, min(step_limit, delta))
        if abs(self.actual_hz) < 0.05:
            self.actual_hz = 0.0

        airflow = self.actual_hz / cfg.NOMINAL_HZ          # 0..1

        # First-order thermal approach: full airflow -> cold, no airflow -> hot
        equilibrium = cfg.AMBIENT_HOT - (cfg.AMBIENT_HOT - cfg.AMBIENT_COLD) * airflow
        self.inlet_temp += (equilibrium - self.inlet_temp) * cfg.TEMP_RATE

        # Derived electrical telemetry
        current_a = 2.0 + 20.0 * airflow
        torque_pct = 15.0 + 60.0 * airflow
        motor_thermal = 30.0 + 40.0 * airflow
        drive_thermal = 25.0 + 30.0 * airflow
        motor_voltage = int(400 * airflow)
        rpm = int(airflow * cfg.MOTOR_RPM_MAX)

        crit = self.inlet_temp >= cfg.CRIT_C
        self.faulted = crit
        if crit:
            eta = cfg.ETA_FAULT                                 # real trip: OE/run drop, fault bit 3 latches
        else:
            eta = cfg.ETA_RUNNING if running else cfg.ETA_READY_STOPPED

        # Publish telemetry to registers
        write_reg(cfg.REG_RFR, int(self.actual_hz * 10))
        write_reg(cfg.REG_RFRD, rpm)
        write_reg(cfg.REG_LCR, int(current_a * 10))
        write_reg(cfg.REG_OTR, int(torque_pct * 10))
        write_reg(cfg.REG_THR, int(motor_thermal))
        write_reg(cfg.REG_THD, int(drive_thermal))
        write_reg(cfg.REG_UOP, motor_voltage)
        write_reg(cfg.REG_ETA, eta)
        # Integrator process tag: cooling-loop inlet temperature (0.1 deg C)
        write_reg(cfg.REG_INLET_TEMP, int(self.inlet_temp * 10))

        # Fault-log block: armed at thermal-critical, cleared once cooling recovers.
        if crit and not self.impact_latched:
            write_ascii(
                cfg.REG_FAULTLOG_BASE,
                "FAULT THERMAL-CRIT COOLING-LOST " + cfg.FLAG_IMPACT,
            )
            self.impact_latched = True
            log.critical(
                "THERMAL CRITICAL: inlet=%.1fC airflow=%.0f%%",
                self.inlet_temp, airflow * 100,
            )
        elif self.impact_latched and self.inlet_temp < cfg.WARN_C:
            clear_block(cfg.REG_FAULTLOG_BASE, 48)
            self.impact_latched = False
            log.info("cooling recovered: fault-log cleared")

        return {
            "cmd": cmd,
            "lfr_hz": lfr / 10.0,
            "running": running,
            "actual_hz": round(self.actual_hz, 1),
            "airflow_pct": round(airflow * 100, 1),
            "inlet_temp": round(self.inlet_temp, 1),
            "rpm": rpm,
            "faulted": crit,
        }


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
def start_server():
    identity = build_identity()
    log.info("ATV630 Modbus/TCP listening on %s:%s", cfg.MODBUS_HOST, cfg.MODBUS_PORT)
    StartTcpServer(context=context, address=(cfg.MODBUS_HOST, cfg.MODBUS_PORT),
                   identity=identity)


def start_server_thread() -> threading.Thread:
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(1.0)   # let the listener bind before physics starts
    return t
