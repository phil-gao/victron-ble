# Duty-cycled Victron logger (fork addition)

`victron-duty-cycle-logger.py` — a thin wrapper around this repo's `victron-ble read`
CLI that **duty-cycles the scan** so a Victron passive scanner can coexist with a
*held* BLE connection to another device on the **same single radio**.

## Why

`victron-ble read` scans continuously. On a single-radio host (e.g. a Raspberry Pi
with a shared Wi-Fi/BT chip), continuous BLE scanning **starves a concurrent GATT
connection** — the radio can't both scan and reliably hold a link. In my truck the
other device is a Dometic CFX3 fridge (see
[cfx3-ble-logger](https://github.com/phil-gao/cfx3-ble-logger)): with Victron
scanning non-stop, the fridge connection dropped roughly once a minute.

Victron broadcasts its Instant Readout advertisement about once a second, so it
doesn't need the radio continuously — a short scan window catches every device.
This wrapper scans for a few seconds, then **frees the radio** for ~20+ seconds,
and repeats. The fridge connection stays up; Victron readings land every ~30 s
(plenty for battery/solar data).

## Use

```python
SCAN_SECS, IDLE_SECS = 8, 22   # ~30s cycle; radio free ~73% of the time
```

Writes `victron-latest.json` + a daily `victron-<YYYYMMDD>.jsonl`. Adjust for your
setup: the output dir, the device config path (`~/.config/victron/devices.json`,
shaped `{"name": {"mac": "...", "key": "..."}}`), and the `NAME_OVERRIDE` map.
Runs as a systemd service in the truck.

Everything else in this repo is keshavdv's upstream `victron_ble` library, unchanged.
