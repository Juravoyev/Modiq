# Serverga joylash (AWS EC2)

Loyiha serverda uchta Docker konteynerda ishlaydi (`docker-compose.prod.yml`):

| Konteyner | Vazifasi |
|---|---|
| `db` | PostgreSQL 16. Port tashqariga ochilmaydi |
| `backend` | Django + Gunicorn. Ishga tushganda `migrate` va `collectstatic` ni o'zi bajaradi |
| `web` | Nginx: React ilovasini beradi, `/api/` va `/admin/` ni backendga yo'naltiradi, `/static/` va `/media/` fayllarini beradi |

Tashqariga faqat 80-port ochiladi. Ishga tushgandan keyin:

- Ilova: `http://<IP>/`
- Swagger: `http://<IP>/api/docs/`
- Admin: `http://<IP>/admin/`

## 1. EC2 server yaratish

AWS Console → **EC2** → **Launch instance**:

1. **Name:** `modiq`
2. **AMI:** Ubuntu Server 24.04 LTS (*Free tier eligible*)
3. **Instance type:** *Free tier eligible* belgisi bor turi (`t2.micro` yoki `t3.micro`, 1 GB RAM)
4. **Key pair:** *Create new key pair* → nomi `modiq`, turi RSA, formati `.pem`. Yuklab olingan faylni saqlab qo'ying: uni qayta yuklab bo'lmaydi
5. **Network settings → Edit:**
   - SSH (22): Source = *My IP*
   - *Add security group rule*: HTTP (80), Source = *Anywhere (0.0.0.0/0)*
6. **Storage:** 20 GB gp3 (free tier 30 GB gacha)
7. **Launch instance**

Instance ro'yxatida *Public IPv4 address* ni ko'chirib oling (pastda `<IP>` deb yozilgan joylarga qo'yiladi).

> IP manzil instance to'xtatilib qayta yoqilsa o'zgaradi. Doimiy manzil kerak bo'lsa, **Elastic IP** ajratib, instance'ga biriktiring (ishlab turgan instance'ga biriktirilgan bo'lsa, to'lovsiz).

## 2. Serverga ulanish

```bash
chmod 400 ~/Downloads/modiq.pem
ssh -i ~/Downloads/modiq.pem ubuntu@<IP>
```

## 3. Serverni tayyorlash (bir marta)

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

`exit` dan keyin qayta `ssh` bilan ulaning (docker guruhi yangi sessiyada kuchga kiradi). Tekshirish: `docker compose version`.

## 4. Loyihani yuklab olish va sozlash

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

`nano .env.prod` bilan oching va quyidagilarni o'zgartiring:

- `SECRET_KEY` va `POSTGRES_PASSWORD`: yuqoridagi buyruqlar chiqargan qiymatlar
- `ALLOWED_HOSTS=<IP>`
- `CSRF_TRUSTED_ORIGINS=http://<IP>`
- `GEMINI_API_KEY`: AI yordamchi va tavsiyalar xulosasi uchun (ixtiyoriy)

Saqlash: `Ctrl+O`, `Enter`, chiqish: `Ctrl+X`.

## 5. Ishga tushirish

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Birinchi marta 5-10 daqiqa oladi (image'lar yuklanadi, frontend yig'iladi). Holatni tekshirish:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend
```

Brauzerda `http://<IP>/api/docs/` ni oching.

Demo do'kon va admin foydalanuvchi:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py seed_demo
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py createsuperuser
```

Demo kirish ma'lumotlari README da: `+998 90 000 00 01`, parol `Demo-12345`.

Har safar uzun buyruq yozmaslik uchun alias qo'shish mumkin:

```bash
echo "alias dc='docker compose -f ~/Modiq/docker-compose.prod.yml --env-file ~/Modiq/.env.prod'" >> ~/.bashrc
source ~/.bashrc
dc ps
```

## 6. Swagger'da sinash

1. `POST /api/auth/login/` → *Try it out* → telefon va parol → *Execute*. Javobdan `access` tokenni ko'chiring
2. Yuqoridagi **Authorize** tugmasi → tokenni qo'ying → *Authorize*
3. Endi istalgan endpointni chaqirish mumkin, masalan `GET /api/catalog/products/`

## 7. Yangilash

GitHub'ga yangi o'zgarish yuklangandan keyin, serverda:

```bash
cd ~/Modiq
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Migratsiyalar backend qayta ishga tushganda avtomatik bajariladi. Ma'lumotlar (`pgdata`, `media` volume'lari) saqlanib qoladi.

## 8. Zaxira nusxa (backup)

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db pg_dump -U modiq modiq | gzip > modiq-$(date +%F).sql.gz
```

Tiklash:

```bash
gunzip -c modiq-2026-11-10.sql.gz | docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db psql -U modiq modiq
```

## Muammolar

| Belgisi | Sababi va yechimi |
|---|---|
| Sahifa ochilmaydi | Security group'da 80-port ochiqmi? `docker compose ... ps` da hamma konteyner `Up`mi? |
| `Bad Request (400)` | `.env.prod` dagi `ALLOWED_HOSTS` da IP yo'q. Tuzatib, `up -d` ni qayta bajaring |
| `/admin/` ga kirishda CSRF xatosi | `CSRF_TRUSTED_ORIGINS=http://<IP>` va `SECURE_COOKIES=False` ekanini tekshiring |
| Build paytida `Killed` | Xotira yetmadi: swap qo'shilganini tekshiring (`free -h`) |
| `502 Bad Gateway` | Backend hali ishga tushmagan yoki xato bilan to'xtagan: `logs backend` |

## HTTPS (keyinroq)

Domen olingandan keyin Let's Encrypt (certbot) bilan HTTPS sozlanadi va `.env.prod` da `SECURE_COOKIES=True` qilinadi. HTTPS bo'lmasa ham API va Swagger to'liq ishlaydi, faqat PWA'ni telefonga o'rnatish uchun HTTPS kerak.
