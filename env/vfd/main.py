"""ATV630 simulator entry point: start Modbus server, seed drive, run physics loop."""

import logging
import time

import atv630
import config as cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
log = logging.getLogger("main")


def main() -> None:
    atv630.start_server_thread()
    atv630.seed_registers()
    plant = atv630.Plant()
    log.info("ATV630 seeded to normal operation (CMD=RUN, LFR=%.1f Hz)", cfg.NOMINAL_HZ)

    tick = 0
    while True:
        state = plant.step()
        if tick % 5 == 0:                      # keep the log readable
            log.info(
                "hz=%(actual_hz)s air=%(airflow_pct)s%% inlet=%(inlet_temp)sC "
                "run=%(running)s fault=%(faulted)s",
                state,
            )
        tick += 1
        time.sleep(cfg.TICK_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Stopping ATV630 simulator.")
