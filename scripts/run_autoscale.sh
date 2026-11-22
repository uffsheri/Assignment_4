#!/bin/bash
# Autoscaling test: 2 min @ 10 req/s, 5 min @ 100 req/s, 3 min @ 10 req/s (10 minutes total).
# Run from the project root:  ./scripts/run_autoscale.sh
HOST=${TARGET_HOST:-emi.local}
PORT=${TARGET_PORT:-80}
PHASES=${PHASES:-"10:120 100:300 10:180"}        # rate:seconds
PROFILE_INTERVAL=${PROFILE_INTERVAL:-15}
OUT=results/autoscale
mkdir -p "$OUT" /tmp/emi-sessions

echo "=== Reset: single replica, fresh HPA"
kubectl delete hpa emi-web -n emi --ignore-not-found
kubectl scale deployment emi-web --replicas=1 -n emi
kubectl rollout status deployment/emi-web -n emi --timeout=180s
sleep "${SETTLE:-30}"
kubectl apply -f k8s/08-hpa.yaml
sleep "${SETTLE:-30}"                                  # let the HPA read its first metrics
kubectl get hpa emi-web -n emi

# Pre-generate every phase's request file so there is no gap between phases
i=0
for ph in $PHASES; do
  i=$((i + 1)); rate=${ph%%:*}; secs=${ph##*:}
  python3 scripts/gen_sessions.py $((rate * secs)) "/tmp/emi-sessions/auto_$i.txt" $((i * 77)) > /dev/null
done

python3 scripts/profile.py "$OUT/autoscale" --hpa --interval "$PROFILE_INTERVAL" &
PROF=$!
sleep 2
echo "timestamp,rate_req_per_s" > "$OUT/phases.csv"

i=0
for ph in $PHASES; do
  i=$((i + 1)); rate=${ph%%:*}; secs=${ph##*:}
  echo ">>> $(date +%T) phase $i: $rate req/s for $secs s"
  echo "$(date '+%Y-%m-%d %H:%M:%S'),$rate" >> "$OUT/phases.csv"
  httperf --hog --server "$HOST" --port "$PORT" \
          --add-header 'Content-Type: application/json\n' \
          --wsesslog=$((rate * secs)),0,"/tmp/emi-sessions/auto_$i.txt" \
          --rate="$rate" --timeout=5 > "$OUT/phase${i}_httperf.txt" 2>&1
done
echo "$(date '+%Y-%m-%d %H:%M:%S'),0" >> "$OUT/phases.csv"     # end marker
sleep 5
kill "$PROF"; wait "$PROF" 2>/dev/null
echo "=== Finished. Final HPA state:"; kubectl get hpa emi-web -n emi
