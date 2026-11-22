#!/usr/bin/env python3
"""Generate an httperf --wsesslog file: N sessions, each one POST /api/emi with random valid inputs.
usage: gen_sessions.py <count> <outfile> [seed]"""
import json, random, sys

count = int(sys.argv[1])
out = sys.argv[2]
rnd = random.Random(int(sys.argv[3])) if len(sys.argv) > 3 else random.Random()

with open(out, "w") as f:
    for _ in range(count):
        body = {
            "principal": rnd.randrange(10000, 5000001, 1000),
            "rate": round(rnd.uniform(1, 30), 1),
            "months": rnd.randint(6, 360),
        }
        f.write("/api/emi method=POST contents='%s'\n\n" % json.dumps(body, separators=(",", ":")))
print("wrote %d sessions to %s" % (count, out))
