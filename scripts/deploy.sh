#!/usr/bin/env bash
# GitHub'dagi yangi kodni serverga qo'llaydi. Serverda:  ~/Modiq/scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

git pull --ff-only
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker image prune -f >/dev/null   # eski image'lar diskni to'ldirmasin
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
echo "Yangilandi: $(git log -1 --format='%h %s')"
