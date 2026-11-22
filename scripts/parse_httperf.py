#!/usr/bin/env python3
"""Parse one httperf output file and print one CSV row (with header if --header).
usage: parse_httperf.py <httperf_output.txt> <replicas> <rate> [--header]"""
import re, sys

path, replicas, rate = sys.argv[1], sys.argv[2], sys.argv[3]
t = open(path).read()

def grab(pattern, default=""):
    m = re.search(pattern, t)
    return m.group(1) if m else default

requests = grab(r"Total: connections \d+ requests (\d+)")
replies = grab(r"replies (\d+) test-duration")
duration = grab(r"test-duration ([\d.]+) s")
resp = grab(r"Reply time \[ms\]: response ([\d.]+)")
xfer = grab(r"Reply time \[ms\]: response [\d.]+ transfer ([\d.]+)")
avg_ms = round(float(resp) + float(xfer or 0), 1) if resp else ""
errors = grab(r"Errors: total (\d+)", "0")
s2xx = grab(r"2xx=(\d+)", "0")
s4xx = grab(r"4xx=(\d+)", "0")
s5xx = grab(r"5xx=(\d+)", "0")
rr = grab(r"Reply rate \[replies/s\]: min [\d.]+ avg ([\d.]+)")
non2xx = int(s4xx) + int(s5xx)

cols = ["replicas", "target_rate", "requests_sent", "replies", "avg_response_ms",
        "errors_total", "http_4xx", "http_5xx", "avg_reply_rate", "duration_s"]
if "--header" in sys.argv:
    print(",".join(cols))
print(",".join(str(x) for x in [replicas, rate, requests, replies, avg_ms, errors, s4xx, s5xx, rr, duration]))
