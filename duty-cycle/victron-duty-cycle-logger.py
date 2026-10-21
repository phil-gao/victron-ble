#!/usr/bin/env python3
"""Victron BLE logger (DUTY-CYCLED): brief scan windows so the radio is free
for the CFX3 fridge connection most of the time. Victron broadcasts ~1/s, so a
short window catches every device; readings land every ~SCAN+IDLE seconds."""
import json, os, pathlib, select, signal, subprocess, time

CFG = pathlib.Path.home() / ".config/victron/devices.json"
OUT = pathlib.Path("/var/lib/gxpi")
NAME_OVERRIDE = {"VE.Direct Smart": "XPLORGX Inverter"}
SCAN_SECS, IDLE_SECS = 8, 22        # ~30s cycle; radio free ~73% of the time

devs = json.loads(CFG.read_text())
args = [str(pathlib.Path.home() / ".local/bin/victron-ble"), "read"]
args += [f"{v['mac']}@{v['key']}" for v in devs.values()]

latest, last_snap = {}, 0.0


def collect() -> None:
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, preexec_fn=os.setsid)
    t0 = time.time()
    try:
        while time.time() - t0 < SCAN_SECS:
            remaining = SCAN_SECS - (time.time() - t0)
            r, _, _ = select.select([p.stdout], [], [], max(0.1, remaining))
            if not r:
                continue
            line = p.stdout.readline().strip()
            if not line.startswith("{"):
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            name = rec.get("name") or rec.get("address")
            name = NAME_OVERRIDE.get(name, name)
            latest[name] = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                            "rssi": rec.get("rssi"), **rec.get("payload", {})}
    finally:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            p.wait(timeout=5)
        except Exception:
            try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception: pass


while True:
    collect()
    if latest:
        OUT.mkdir(exist_ok=True)
        (OUT / "victron-latest.json").write_text(
            json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "devices": latest}))
        now = time.time()
        if now - last_snap > 60:
            with open(OUT / f"victron-{time.strftime('%Y%m%d')}.jsonl", "a") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "devices": latest}) + "\n")
            last_snap = now
    time.sleep(IDLE_SECS)
