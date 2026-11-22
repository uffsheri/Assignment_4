#!/bin/bash
# Fixed-replica experiments: replicas {1,2,3} x rates {10,25,50,100,200} req/s, 60 s each = 15 runs.
# Run from the project root:  ./scripts/run_experiments.sh
# Optional env overrides (for resuming / quick tests):
#   REPLICAS_LIST="1 2 3"  RATES="10 25 50 100 200"  DURATION=60  COOLDOWN=30
HOST=${TARGET_HOST:-emi.local}
PORT=${TARGET_PORT:-80}
DURATION=${DURATION:-60}
REPLICAS_LIST=${REPLICAS_LIST:-"1 2 3"}
RATES=${RATES:-"10 25 50 100 200"}
COOLDOWN=${COOLDOWN:-30}
PROFILE_INTERVAL=${PROFILE_INTERVAL:-15}
OUT=results/experiments
SUMMARY=results/summary.csv
mkdir -p "$OUT" /tmp/emi-sessions

[ -f "$SUMMARY" ] || python3 scripts/parse_httperf.py /dev/null 0 0 --header | head -1 > "$SUMMARY"

kubectl delete hpa emi-web -n emi --ignore-not-found      # the HPA must not fight our manual scaling

for r in $REPLICAS_LIST; do
  echo "=== Scaling emi-web to $r replica(s)"
  kubectl scale deployment emi-web --replicas="$r" -n emi
  kubectl rollout status deployment/emi-web -n emi --timeout=180s
  kubectl get pods -n emi -l app=emi-web --no-headers | tee "$OUT/pods_before_r${r}.txt"
  sleep "${SETTLE:-20}"                                       # let metrics and connections settle

  for rate in $RATES; do
    tag=r${r}_rate${rate}
    n=$((rate * DURATION))
    python3 scripts/gen_sessions.py "$n" "/tmp/emi-sessions/$tag.txt" $((r * 1000 + rate)) > /dev/null
    echo ">>> $(date +%T)  replicas=$r  rate=$rate req/s  ($n requests)"

    python3 scripts/profile.py "$OUT/$tag" --interval "$PROFILE_INTERVAL" &
    PROF=$!
    sleep 2
    httperf --hog --server "$HOST" --port "$PORT" \
            --add-header 'Content-Type: application/json\n' \
            --wsesslog="$n",0,"/tmp/emi-sessions/$tag.txt" \
            --rate="$rate" --timeout=5 > "$OUT/${tag}_httperf.txt" 2>&1
    sleep 3
    kill "$PROF"; wait "$PROF" 2>/dev/null

    python3 scripts/parse_httperf.py "$OUT/${tag}_httperf.txt" "$r" "$rate" | tee -a "$SUMMARY"
    sleep "$COOLDOWN"
  done
done
echo "=== Done. Summary:"; cat "$SUMMARY"
