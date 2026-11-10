# Talking to the drive — real Modbus tools

This is a tool reference, not a walkthrough. It teaches the two standard clients a
working engineer actually types. *Which* registers to read or write, and what the
values mean, is yours to discover from the drive, the notes you find, the process
historian, and the vendor manual. This page only shows you how to drive the tools.

## Where to run them

The control network is not reachable from your starting IT host. Run these from the
**Engineering Workstation** once you are on it — it is the one machine with a leg on
both networks, and both tools are already installed there. The drive answers Modbus/TCP
on port **502**, unit id **1**.

## The one gotcha that wastes the most time: `-0`

This drive is **zero-based on the wire** (register N is at index N). `mbpoll` defaults to
one-based addressing, so **always pass `-0`**. Without it every address lands one
register off and you will chase values that aren't there.

## `mbpoll` — read and write holding registers

```
mbpoll -0 -1 -m tcp -a 1 -t 4 -r <start> -c <count> <drive-ip>
```

| flag | meaning |
|------|---------|
| `-0` | zero-based addressing (mandatory here) |
| `-1` | one-shot (poll once and exit; drop it to poll continuously) |
| `-m tcp` | Modbus/TCP |
| `-a 1` | unit / slave id 1 |
| `-t 4` | holding registers (the 4xxxx table) |
| `-r` | start register (decimal) |
| `-c` | how many registers to read |

Read example (status word — safe, read-only telemetry you can also see on the HMI):

```
mbpoll -0 -1 -m tcp -a 1 -t 4 -r 3201 -c 1 <drive-ip>
```

**Write** a single holding register by putting the value at the end and dropping `-c`:

```
mbpoll -0 -m tcp -a 1 -t 4 -r <register> <drive-ip> <value>
```

A write changes the live process. Know what a register does and what its normal value
is before you touch it, and record the baseline so you can put it back.

## `pymodbus.console` — the interactive client (device identity)

```
pymodbus.console tcp --host <drive-ip> --port 502
```

That drops you into a REPL. The device-identity request (Modbus FC43 / MEI 14) is how a
drive reports its make and model:

```
client.read_device_information read_code=3
```

The output is raw JSON of identity objects. A basic read returns very little on purpose —
the useful objects only show up on the **extended** read (`read_code=3`).

One-liner, if the console is awkward:

```
python3 -c "from pymodbus.client import ModbusTcpClient as C; c=C('<drive-ip>'); c.connect(); print(c.read_device_information(read_code=3).information)"
```

## Watching your work

Keep the operator dashboard open at **http://localhost:8080** while you work. Reads won't
change it; a write that actually affects the process will show up there in real time.
