#!/usr/bin/env python3
"""Make the three required graphs from the files in results/.  Run from the project root:
    python3 scripts/plot_graphs.py
Writes results/graphs/graph1_response_time.png, graph2_pod_cpu.png, graph3_autoscaling.png"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Colours: validated categorical palette slots 1-3 (blue, orange, aqua) on a light surface
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
CAT = [BLUE, ORANGE, AQUA]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
    "legend.frameon": False,
})
os.makedirs("results/graphs", exist_ok=True)

# ---------- Graph 1: average response time vs request rate ----------
s = pd.read_csv("results/summary.csv")
rates = sorted(s["target_rate"].unique())
fig, ax = plt.subplots(figsize=(8, 4.8))
for color, (n, g) in zip(CAT, s.groupby("replicas")):
    g = g.sort_values("target_rate")
    xs = [rates.index(r) for r in g["target_rate"]]
    ax.plot(xs, g["avg_response_ms"], color=color, linewidth=2, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label=f"{n} replica" + ("s" if n > 1 else ""))
ax.set_xticks(range(len(rates))); ax.set_xticklabels(rates)
ax.set_xlabel("Request rate (requests/s)"); ax.set_ylabel("Average response time (ms)")
ax.set_title("Graph 1: Average response time vs request rate", loc="left", color=INK)
ax.legend(title="Web replicas", loc="upper left")
fig.tight_layout(); fig.savefig("results/graphs/graph1_response_time.png", dpi=200); plt.close(fig)

# ---------- Graph 2: per-pod CPU utilisation, 100 req/s, 3 replicas ----------
REQUEST_M = 100.0     # CPU request per pod (millicores): utilisation % = usage / request, as the HPA computes it
d = pd.read_csv("results/experiments/r3_rate100_pods.csv", parse_dates=["timestamp"])
d = d[d["pod"].str.startswith("emi-web")].copy()
d["t"] = (d["timestamp"] - d["timestamp"].min()).dt.total_seconds()
d["cpu_pct"] = d["cpu_millicores"] / REQUEST_M * 100
fig, ax = plt.subplots(figsize=(8, 4.8))
for color, (pod, g) in zip(CAT, d.groupby("pod")):
    ax.plot(g["t"], g["cpu_pct"], color=color, linewidth=2, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label=pod.split("-", 2)[-1])
ax.set_xlabel("Time since first sample (s)"); ax.set_ylabel("CPU utilisation (% of 100m request)")
ax.set_ylim(bottom=0)
ax.set_title("Graph 2: Per-pod CPU, 100 req/s with 3 replicas", loc="left", color=INK)
ax.legend(title="Pod (emi-web-...)", loc="upper left", bbox_to_anchor=(1.01, 1))
fig.tight_layout(); fig.savefig("results/graphs/graph2_pod_cpu.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- Graph 3: autoscaling test, shared time axis ----------
ph = pd.read_csv("results/autoscale/phases.csv", parse_dates=["timestamp"])
h = pd.read_csv("results/autoscale/autoscale_hpa.csv", parse_dates=["timestamp"])
t0 = ph["timestamp"].min()
ph["t"] = (ph["timestamp"] - t0).dt.total_seconds() / 60
h["t"] = (h["timestamp"] - t0).dt.total_seconds() / 60
h = h[h["t"] >= -0.1]
h["cpu"] = pd.to_numeric(h["avg_cpu_utilization_percent"], errors="coerce")
h["rep"] = pd.to_numeric(h["current_replicas"], errors="coerce")

fig, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
axes[0].step(ph["t"], ph["rate_req_per_s"], where="post", color=BLUE, linewidth=2)
axes[0].set_ylabel("Request rate (req/s)"); axes[0].set_ylim(bottom=0)
axes[1].plot(h["t"], h["cpu"], color=ORANGE, linewidth=2)
axes[1].axhline(50, color=MUTED, linewidth=1.2, linestyle="--")
axes[1].text(0.15, 54, "HPA target 50%", color=MUTED, fontsize=9, va="bottom")
axes[1].set_ylabel("Avg CPU utilisation (%)"); axes[1].set_ylim(bottom=0)
axes[2].step(h["t"], h["rep"], where="post", color=AQUA, linewidth=2)
axes[2].set_ylabel("Web replicas"); axes[2].set_ylim(0, 5.5); axes[2].set_yticks(range(0, 6))
axes[2].set_xlabel("Time since start of test (minutes)")
axes[0].set_title("Graph 3: Autoscaling test (10 -> 100 -> 10 req/s)", loc="left", color=INK)
fig.tight_layout(); fig.savefig("results/graphs/graph3_autoscaling.png", dpi=200); plt.close(fig)
print("Saved graphs in results/graphs/")
