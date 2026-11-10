# Data Center Cooling — OT Assessment (ATV630)

An authorized assessment of a **simulated** data-center cooling cell. You
start with access to the corporate IT network. Somewhere past it is the
control network that runs the Row A cooling loop: a Schneider Electric drive
turning a fan, and an operator screen watching the cold aisle. Your job is to
work in, reach the process, and prove that an unauthorized action can put the
data center into a thermal emergency — then write it up.

> **Scope: simulated systems only. No scanning or control of real equipment.**
> Fork of Neil Brandon's [MOCS_2026](https://github.com/NeilBrandon/MOCS_2026).

This is the capstone. It expects the whole semester: network discovery, network
scanning, web-application testing, cracking, vendor research, and
control-protocol work.

> New to the Modbus tools? [`modbus-tools.md`](modbus-tools.md) is a tool reference
> for `mbpoll` and the `pymodbus` console — syntax only, no spoilers.

---

## Ground rules

- Authorized assessment of the lab environment only. Nothing here talks to the
  internet or to real hardware.
- Everything you need is inside the environment or is public vendor
  documentation you can find from your own machine. No insider hints are planted.
- One controlled, documented impact is the objective. Capture the flags, then
  restore normal operation.

## Objective — six flags

There are six `FLAG{...}` tokens, one per stage of a realistic sequence of steps,
from first access to process impact. You find them by doing the work; nothing in the
environment tells you where they are or what to do. Point split:

| Stage | Points |
|-------|:------:|
| Web access | 10 |
| System access | 10 |
| Device identification | 10 |
| Process discovery | 10 |
| Process-history extraction | 20 |
| Process impact | 25 |
| Report | 15 |


---

## Bring the lab up

Requires Docker + the compose plugin. First build needs internet to pull base
images and packages; after that the lab runs fully offline.

```bash
cd env
docker compose up -d --build
docker compose ps                 # toolbox, ews, vfd, hmi, historian  (all Up)
```

Operator screen (leave it visible in a browser):

```
http://localhost:8080
```

Open a shell on your toolbox host on the IT network:

```bash
docker exec -it toolbox bash
```

From there, it's yours to enumerate. Teardown: `docker compose down`.

---

## Containment / "no internet"

Both internal networks are Docker `internal: true`: the toolbox host, the
workstation, and the drive have **no route to the internet** and cannot be
reached from it. Every tool is baked into the images at build time. The only
port published to your host is the operator screen (`8080`), so you can watch it.

Do your vendor research (device manuals, protocol references) on **your own
machine's browser**, the same way a real assessor would — the lab targets stay
air-gapped.

> To pre-stage an offline classroom: build once on a connected machine, then
> `docker save` the images and load them on the lab machines.

---

## What to hand in

An assessment report, same standard as the hardware final:

- Executive summary — what someone with this access could do to the cooling
  process and why it matters.
- The full sequence, stage by stage, with the commands and evidence you used and a
  captured flag for each stage.
- Root cause — not "the drive has a bug" (it doesn't), but *why the network let
  an unauthorized command through*.
- Remediation — how you would stop this, in OT terms.

---

## Layout

```
env/                     the lab environment (docker compose)
modbus-tools.md          tool reference for mbpoll and the pymodbus console
OT Final Project - Student Guide.pptx   project brief and rubric
```
