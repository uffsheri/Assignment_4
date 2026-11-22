#!/usr/bin/env python3
"""Profiler: saves host CPU (every 1 s) and per-pod CPU/memory (kubectl top, every 15 s) to CSV files,
optionally also the HPA state (every 15 s). Stops on Ctrl+C / SIGTERM.
usage: profile.py <out_prefix> [--hpa] [--namespace emi] [--interval 15]
Creates: <out_prefix>_host_cpu.csv, <out_prefix>_pods.csv, and with --hpa: <out_prefix>_hpa.csv + <out_prefix>_hpa_raw.txt"""
import argparse, csv, json, signal, subprocess, threading, time
import psutil

p = argparse.ArgumentParser()
p.add_argument("prefix")
p.add_argument("--namespace", default="emi")
p.add_argument("--interval", type=float, default=15)
p.add_argument("--hpa", action="store_true")
a = p.parse_args()

stop = threading.Event()
def _stop(*_):
    stop.set()
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return ""

def cpu_to_m(s):
    return float(s[:-1]) if s.endswith("m") else float(s) * 1000

def mem_to_mib(s):
    units = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024}
    for u, f in units.items():
        if s.endswith(u):
            return float(s[:-2]) * f
    return float(s) / (1024 * 1024)

def every(period, fn):
    nxt = time.time()
    while not stop.is_set():
        fn()
        nxt += period
        stop.wait(max(0, nxt - time.time()))

def host_cpu(w, f):
    while not stop.is_set():
        v = psutil.cpu_percent(interval=1)      # blocks 1 s, so one row per second
        w.writerow([now(), v]); f.flush()

def top(w, f):
    def once():
        t = now()
        for line in run(["kubectl", "top", "pods", "-n", a.namespace, "--no-headers"]).splitlines():
            parts = line.split()
            if len(parts) >= 3:
                w.writerow([t, parts[0], cpu_to_m(parts[1]), round(mem_to_mib(parts[2]), 1)])
        f.flush()
    every(a.interval, once)

def hpa(w, f, raw):
    def once():
        t = now()
        txt = run(["kubectl", "get", "hpa", "emi-web", "-n", a.namespace])
        raw.write("[%s]\n%s\n" % (t, txt.strip())); raw.flush()
        js = run(["kubectl", "get", "hpa", "emi-web", "-n", a.namespace, "-o", "json"])
        try:
            d = json.loads(js)
            cur = ""
            for m in d.get("status", {}).get("currentMetrics", []) or []:
                if m.get("type") == "Resource":
                    cur = m["resource"]["current"].get("averageUtilization", "")
            tgt = d["spec"]["metrics"][0]["resource"]["target"]["averageUtilization"]
            w.writerow([t, cur, tgt, d["status"].get("currentReplicas", ""), d["status"].get("desiredReplicas", "")])
        except Exception:
            w.writerow([t, "", "", "", ""])
        f.flush()
    every(a.interval, once)

files, threads = [], []
def opener(name, header):
    f = open(a.prefix + name, "w", newline="")
    w = csv.writer(f); w.writerow(header); files.append(f)
    return w, f

w1, f1 = opener("_host_cpu.csv", ["timestamp", "host_cpu_percent"])
w2, f2 = opener("_pods.csv", ["timestamp", "pod", "cpu_millicores", "memory_mib"])
threads.append(threading.Thread(target=host_cpu, args=(w1, f1)))
threads.append(threading.Thread(target=top, args=(w2, f2)))
if a.hpa:
    w3, f3 = opener("_hpa.csv", ["timestamp", "avg_cpu_utilization_percent", "target_percent", "current_replicas", "desired_replicas"])
    raw = open(a.prefix + "_hpa_raw.txt", "w"); files.append(raw)
    threads.append(threading.Thread(target=hpa, args=(w3, f3, raw)))
for t in threads:
    t.start()
while not stop.is_set():
    stop.wait(0.5)
for t in threads:
    t.join()
for f in files:
    f.close()
