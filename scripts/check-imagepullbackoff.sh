#!/usr/bin/env bash
# scripts/check-imagepullbackoff.sh — fail-loud check for stuck image pulls.
#
# Walks all namespaces and reports any pod in ImagePullBackOff / ErrImagePull
# older than --age (default 5m). Designed to be run on a schedule; exits
# non-zero (with a structured summary on stdout) when stale pull failures
# exist so an alerting layer (CronJob + Slack webhook, or any external
# scheduler) can act.
#
# Why this exists: on May 19 2026, 4 source-* cronjobs in vprod went into
# ImagePullBackOff after a values bump pointed them at tags that were never
# published to GHCR. They stayed broken for 8 days before anyone noticed
# because nothing was watching for them. See this file's sibling
# planning/release-process.md.

set -euo pipefail

AGE_MIN="${AGE_MIN:-5}"           # override via env or --age
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}" # override via env or --slack-webhook

while [[ $# -gt 0 ]]; do
    case "$1" in
        --age)            AGE_MIN="$2"; shift 2 ;;
        --slack-webhook)  SLACK_WEBHOOK="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,16p' "$0"
            exit 0
            ;;
        *) echo "unknown flag: $1" >&2; exit 64 ;;
    esac
done

command -v kubectl >/dev/null || { echo "kubectl not installed" >&2; exit 67; }
command -v jq      >/dev/null || { echo "jq not installed"     >&2; exit 67; }

NOW_EPOCH=$(date +%s)
SKIP_NS="kube-system cert-manager ingress-nginx"

# Pull every pod across every namespace and filter to ImagePullBackOff /
# ErrImagePull with age > AGE_MIN. Output is JSON array; empty if clean.
PODS=$(kubectl get pods -A -o json | jq -c '
    [ .items[]
      | select(.status.containerStatuses[]? |
               (.state.waiting?.reason // "") |
               (. == "ImagePullBackOff" or . == "ErrImagePull"))
      | select(([.metadata.namespace] | inside($skip)) | not)
      | {
          namespace: .metadata.namespace,
          name:      .metadata.name,
          age_sec:   ((now - (.metadata.creationTimestamp | fromdateiso8601))),
          containers: [
            .status.containerStatuses[]? |
            select(.state.waiting?.reason == "ImagePullBackOff"
                or .state.waiting?.reason == "ErrImagePull") |
            {name: .name, image: .image, reason: .state.waiting.reason}
          ]
        }
    ]
    | map(select(.age_sec >= ($age_min * 60)))
' --argjson skip "$(printf '%s\n' $SKIP_NS | jq -R . | jq -s .)" --argjson age_min "$AGE_MIN")

COUNT=$(printf '%s' "$PODS" | jq 'length')

if [[ "$COUNT" -eq 0 ]]; then
    echo "ok: no pods stuck in ImagePullBackOff/ErrImagePull for >= ${AGE_MIN}m"
    exit 0
fi

# Build a human + Slack-friendly summary.
SUMMARY=$(printf '%s' "$PODS" | jq -r '
    ["namespace/name", "age", "image"] as $h |
    $h, (.[] | [.namespace + "/" + .name,
                (.age_sec / 60 | floor | tostring) + "m",
                (.containers[0].image // "?")])
    | @tsv
')

printf 'STALE ImagePullBackOff detected (%d pods, threshold %dm):\n' "$COUNT" "$AGE_MIN"
printf '\n%s\n' "$SUMMARY" | column -t -s $'\t'

if [[ -n "$SLACK_WEBHOOK" ]]; then
    PAYLOAD=$(jq -nc --arg txt "$(printf 'STALE ImagePullBackOff (%d pods):\n```\n%s\n```' "$COUNT" "$SUMMARY")" \
                  '{text: $txt}')
    curl -sS -X POST -H 'Content-Type: application/json' --data "$PAYLOAD" "$SLACK_WEBHOOK" \
        >/dev/null || true
fi

exit 1
