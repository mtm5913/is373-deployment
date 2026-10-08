#!/usr/bin/env bash
set -euo pipefail

export ENVIRONMENT="${1:?Missing environment}"
COMMIT="${2:?Missing commit}"

case "$ENVIRONMENT" in
  qa) export SITE_HOST="qa.megan373lab.xyz" ;;
  production) export SITE_HOST="megan373lab.xyz" ;;
  *) echo "Invalid environment"; exit 1 ;;
esac

[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || exit 1
export IMAGE="ghcr.io/mtm5913/is373-deployment:$COMMIT"

cd "$(dirname "$0")/.."
PROJECT="is373-$ENVIRONMENT"

docker compose -p "$PROJECT" config --quiet
docker compose -p "$PROJECT" pull

docker compose -p "$PROJECT" up -d

expected=$(sha256sum index.html | cut -d ' ' -f1)
for attempt in $(seq 1 30); do
  actual=$(curl -fsS --connect-timeout 5 --max-time 10 \
    "https://$SITE_HOST/" | sha256sum | cut -d ' ' -f1) || actual=""
  if [ "$actual" = "$expected" ]; then
    echo "Verified https://$SITE_HOST/ at commit $COMMIT"
    printf '%s\n' "$COMMIT" > deployed-commit.txt
    exit 0
  fi
  sleep 5
done

echo "Deployment verification failed"
docker compose -p "$PROJECT" logs --tail=30
exit 1
