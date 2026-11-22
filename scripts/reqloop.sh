#!/bin/bash
# usage: ./scripts/reqloop.sh <logfile> [interval_seconds]   (Ctrl+C to stop)
LOG=${1:-results/reqloop.log}
INT=${2:-0.5}
echo "time,http_code,pod" > "$LOG"
while true; do
  RESP=$(curl -s -m 5 -w '\n%{http_code}' -X POST http://emi.local/api/emi \
    -H "Content-Type: application/json" -d '{"principal":500000,"rate":12,"months":24}')
  CODE=$(echo "$RESP" | tail -n1)
  POD=$(echo "$RESP" | head -n1 | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
  echo "$(date +%T),$CODE,${POD:-none}" | tee -a "$LOG"
  sleep "$INT"
done
