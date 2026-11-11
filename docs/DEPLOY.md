# Serverga joylash (AWS EC2)

Loyiha serverda to'rtta Docker konteynerda ishlaydi (`docker-compose.prod.yml`):

| Konteyner | Vazifasi |
|---|---|
| `db` | PostgreSQL 16. Port tashqariga ochilmaydi |
| `backend` | Django + Gunicorn. Ishga tushganda `migrate` va `collectstatic` ni o'zi bajaradi |
| `web` | Nginx: React ilovasini beradi, `/api/` va `/admin/` ni backendga yo'naltiradi, `/static/` va `/media/` fayllarini beradi |
| `caddy` | Tashqi kirish nuqtasi (80, 443). Domen berilsa, Let's Encrypt HTTPS sertifikatini o'zi oladi va yangilaydi |

Ishga tushgandan keyin (domen `modiq.dehqon-ota.uz` bo'lsa):

- Ilova: `https://modiq.dehqon-ota.uz/`
- Swagger: `https://modiq.dehqon-ota.uz/api/docs/`
- Admin: `https://modiq.dehqon-ota.uz/admin/`

## 1. EC2 server

AWS Console → **EC2** → **Launch instance**: Ubuntu Server 24.04 LTS, *Free tier eligible* belgisi bor tur (`t3.micro`), 20 GB disk.

### Elastic IP (doimiy manzil)

Oddiy ommaviy IP instance to'xtatilib qayta yoqilganda o'zgaradi va domen ishlamay qoladi. Shuning uchun:

1. EC2 → **Elastic IPs** → **Allocate Elastic IP address** → **Allocate**
2. Yangi IP ni belgilang → **Actions** → **Associate Elastic IP address** → Instance: `modiq` → **Associate**

Pastda `<IP>` deb yozilgan joylarga shu Elastic IP qo'yiladi.

### Portlarni ochish (Security group)

Instance → **Security** tab → security group nomi (`launch-wizard-1`) → **Edit inbound rules** → **Add rule**:

| Type | Source |
|---|---|
| SSH (22) | allaqachon bor |
| HTTP (80) | Anywhere-IPv4 (0.0.0.0/0) |
| HTTPS (443) | Anywhere-IPv4 (0.0.0.0/0) |

**Save rules**.

## 2. Domen (subdomain)

Mavjud domenga subdomain qo'shiladi, asosiy sayt (`dehqon-ota.uz`) o'zgarmaydi. Eskiz → **Domen** → `dehqon-ota.uz` → **DNS** → **+ Qo'shish**:

| Name | Type | TTL | Record |
|---|---|---|---|
| `modiq` | A | 3600 | `<IP>` |

Tekshirish (5-30 daqiqa ichida ishlaydi): `dig +short modiq.dehqon-ota.uz` buyrug'i `<IP>` ni chiqarishi kerak.

## 3. Serverga ulanish

**Key pair bilan** (instance yaratishda `.pem` yuklab olingan bo'lsa):

```bash
chmod 400 ~/Downloads/modiq.pem
ssh -i ~/Downloads/modiq.pem ubuntu@<IP>
```

**Key pair'siz:** Instance → **Connect** → **EC2 Instance Connect** → Username `ubuntu` → **Connect**. Brauzerda terminal ochiladi.

Keyin o'z kompyuteringizdan oddiy `ssh` bilan ulanish uchun, kompyuteringizda kalit yarating va ochiq qismini serverga qo'shing:

```bash
# o'z kompyuteringizda
ssh-keygen -t ed25519 -f ~/.ssh/modiq_ec2 -N ""
cat ~/.ssh/modiq_ec2.pub
```

```bash
# brauzerdagi EC2 terminalida (yuqoridagi chiqqan qatorni qo'ying)
echo 'ssh-ed25519 AAAA... ' >> ~/.ssh/authorized_keys
```

```bash
# o'z kompyuteringizda
ssh -i ~/.ssh/modiq_ec2 ubuntu@<IP>
```

## Tez yo'l: skriptlar

4-6 bo'limlardagi hamma ishni bitta skript bajaradi (Ubuntu serverda, SSH bilan kirgandan keyin):

```bash
curl -fsSL https://raw.githubusercontent.com/Juravoyev/Modiq/main/scripts/server-setup.sh | bash
```

U domen va Gemini kalitini so'raydi, parollarni o'zi yaratadi, swap, Docker va loyihani o'rnatadi, ishga tushiradi va demo ma'lumotni yuklashni taklif qiladi.

Keyinchalik yangi kodni qo'llash (8-bo'lim o'rniga):

```bash
~/Modiq/scripts/deploy.sh
```

Quyidagi bo'limlar shu skriptlar ichida nima bo'layotganini qadamma-qadam tushuntiradi.

## 4. Serverni tayyorlash (bir marta)

1 GB RAM frontendni yig'ish uchun kamlik qilishi mumkin, shuning uchun 2 GB swap qo'shamiz:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Docker o'rnatish:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit
```

`exit` dan keyin qayta ulaning (docker guruhi yangi sessiyada kuchga kiradi). Tekshirish: `docker compose version`.

## 5. Loyihani yuklab olish va sozlash

```bash
git clone https://github.com/Juravoyev/Modiq.git
cd Modiq
cp .env.prod.example .env.prod
```

Maxfiy qiymatlarni yaratish:

```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_hex(16))"
```

`nano .env.prod` bilan oching va o'zgartiring:

```ini
SITE_ADDRESS=modiq.dehqon-ota.uz
SECRET_KEY=...            # yuqoridagi buyruq chiqargan qiymat
POSTGRES_PASSWORD=...     # yuqoridagi buyruq chiqargan qiymat
ALLOWED_HOSTS=modiq.dehqon-ota.uz,<IP>
CSRF_TRUSTED_ORIGINS=https://modiq.dehqon-ota.uz
SECURE_COOKIES=True
GEMINI_API_KEY=...        # ixtiyoriy: AI yordamchi va tavsiyalar xulosasi
```

Domen yo'q bo'lsa: `SITE_ADDRESS=:80`, `CSRF_TRUSTED_ORIGINS=http://<IP>`, `SECURE_COOKIES=False`.

Saqlash: `Ctrl+O`, `Enter`, chiqish: `Ctrl+X`.

## 6. Ishga tushirish

Uzun buyruqni qisqartirish uchun alias:

```bash
echo "alias dc='docker compose -f ~/Modiq/docker-compose.prod.yml --env-file ~/Modiq/.env.prod'" >> ~/.bashrc
source ~/.bashrc
```

```bash
dc up -d --build
```

Birinchi marta 5-10 daqiqa oladi (image'lar yuklanadi, frontend yig'iladi). Holatni tekshirish:

```bash
dc ps                 # hamma konteyner "Up" bo'lishi kerak
dc logs -f backend    # chiqish: Ctrl+C
dc logs caddy         # HTTPS sertifikati olinganini ko'rish
```

Demo do'kon va admin foydalanuvchi:

```bash
dc exec backend python manage.py seed_demo
dc exec backend python manage.py createsuperuser
```

Demo kirish: `+998 90 000 00 01` (egasi), parol `Demo-12345`. Boshqa xodimlar README da.

## 7. Swagger'da sinash

1. `POST /api/auth/login/` → *Try it out* → telefon va parol → *Execute*. Javobdan `access` tokenni ko'chiring
2. Yuqoridagi **Authorize** tugmasi → tokenni qo'ying → *Authorize*
3. Endi istalgan endpointni chaqirish mumkin, masalan `GET /api/catalog/products/`

## 8. Yangilash

GitHub'ga yangi o'zgarish yuklangandan keyin, serverda:

```bash
cd ~/Modiq
git pull
dc up -d --build
```

Migratsiyalar backend qayta ishga tushganda avtomatik bajariladi. Ma'lumotlar (`pgdata`, `media` volume'lari) saqlanib qoladi.

## 9. Zaxira nusxa (backup)

```bash
dc exec -T db pg_dump -U modiq modiq | gzip > modiq-$(date +%F).sql.gz
```

Tiklash:

```bash
gunzip -c modiq-2026-11-10.sql.gz | dc exec -T db psql -U modiq modiq
```

## Muammolar

| Belgisi | Sababi va yechimi |
|---|---|
| Sahifa ochilmaydi | Security group'da 80 va 443 ochiqmi? `dc ps` da hamma konteyner `Up`mi? |
| HTTPS ishlamaydi, `dc logs caddy` da sertifikat xatosi | DNS hali tarqalmagan yoki noto'g'ri IP: `dig +short modiq.dehqon-ota.uz`. To'g'rilangach `dc restart caddy` |
| `Bad Request (400)` | `.env.prod` dagi `ALLOWED_HOSTS` da domen/IP yo'q. Tuzatib, `dc up -d` |
| `/admin/` ga kirishda CSRF xatosi | `CSRF_TRUSTED_ORIGINS` aynan brauzerdagi manzil (`https://...`) bilan bir xilmi? |
| Build paytida `Killed` | Xotira yetmadi: swap qo'shilganini tekshiring (`free -h`) |
| `502 Bad Gateway` | Backend hali ishga tushmagan yoki xato bilan to'xtagan: `dc logs backend` |
