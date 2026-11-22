#!/bin/bash
# usage: ./scripts/load30.sh <label> [count]
LABEL=${1:?label required, e.g. 3replicas}
N=${2:-30}
RAW=results/m3-$LABEL-raw.txt
for i in $(seq 1 "$N"); do
  curl -s -X POST http://emi.local/api/emi -H "Content-Type: application/json" \
    -d '{"principal":500000,"rate":12,"months":24}' | grep -o '"name":"[^"]*"' | cut -d'"' -f4
done > "$RAW"
echo "Requests served per pod ($LABEL):"
sort "$RAW" | uniq -c | tee results/m3-$LABEL-counts.txt
echo "Total: $(wc -l < "$RAW")"
