#!/usr/bin/env bash
# Yangi Ubuntu serverni 0 dan tayyorlaydi va Modiq'ni ishga tushiradi. Bir marta ishlatiladi.
# Serverda:  curl -fsSL https://raw.githubusercontent.com/Juravoyev/Modiq/main/scripts/server-setup.sh | bash
set -euo pipefail

REPO=https://github.com/Juravoyev/Modiq.git
DIR="$HOME/Modiq"

if ! grep -qi ubuntu /etc/os-release; then
  echo "Bu skript Ubuntu uchun. Instance'ni Ubuntu Server 24.04 bilan qayta yarating." >&2
  exit 1
fi

echo "== 1/5 Swap (1 GB RAM yig'ish uchun kam)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "== 2/5 Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

echo "== 3/5 Loyiha kodi"
[ -d "$DIR" ] || git clone "$REPO" "$DIR"
cd "$DIR"

echo "== 4/5 Sozlamalar (.env.prod)"
if [ ! -f .env.prod ]; then
  read -rp "Domen (masalan modiq.dehqon-ota.uz): " DOMAIN </dev/tty
  read -rp "Gemini API kaliti (bo'sh qoldirsa bo'ladi): " GEMINI </dev/tty
  IP=$(curl -fsS https://checkip.amazonaws.com)
  cp .env.prod.example .env.prod
  chmod 600 .env.prod
  set_env() { sed -i "s|^$1=.*|$1=$2|" .env.prod; }
  set_env SITE_ADDRESS "$DOMAIN"
  set_env SECRET_KEY "$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
  set_env POSTGRES_PASSWORD "$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
  set_env ALLOWED_HOSTS "$DOMAIN,$IP"
  set_env CSRF_TRUSTED_ORIGINS "https://$DOMAIN"
  set_env SECURE_COOKIES True
  set_env GEMINI_API_KEY "$GEMINI"
else
  echo ".env.prod allaqachon bor, o'zgartirilmadi."
fi

if ! grep -q "alias dc=" ~/.bashrc; then
  echo "alias dc='docker compose -f $DIR/docker-compose.prod.yml --env-file $DIR/.env.prod'" >> ~/.bashrc
fi

echo "== 5/5 Ishga tushirish (birinchi marta 5-10 daqiqa)"
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

read -rp "Demo do'kon ma'lumotlari yuklansinmi? (y/n): " SEED </dev/tty
if [ "$SEED" = "y" ]; then
  sudo docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend python manage.py seed_demo
fi

DOMAIN=$(grep '^SITE_ADDRESS=' .env.prod | cut -d= -f2)
echo
echo "Tayyor. 1-2 daqiqadan keyin oching: https://$DOMAIN/api/docs/"
echo "Qayta ulaning (exit, keyin ssh) va 'dc ps' bilan holatni ko'ring."
