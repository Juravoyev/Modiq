# Modiq
Merchandise, warehouse, sales, and decision-support system for small-scale fashion retail.

Kichik kiyim, oyoq kiyim va sumka do'konlari uchun tovar (rang × o'lcham variantlari), ombor, kassa va qaror qabul qilishni qo'llab-quvvatlash tizimi.

## Jonli demo

| | |
|---|---|
| Ilova | https://modiq.dehqon-ota.uz |
| Swagger (API hujjati) | https://modiq.dehqon-ota.uz/api/docs/ |

Demo kirish: telefon `+998 90 000 00 01` (do'kon egasi), parol `Demo-12345`. Sotuvchi ko'rinishi: `+998 90 000 00 03`.
Swagger'da: `POST /api/auth/login/` → javobdagi `access` tokenni **Authorize** tugmasiga qo'ying.

## Texnologiyalar

- **Backend:** Python 3.12, Django 5.1, Django REST Framework, JWT (SimpleJWT), PostgreSQL 16, drf-spectacular (Swagger)
- **Frontend:** React 19, TypeScript, Vite (PWA)
- **Infratuzilma:** Docker Compose (PostgreSQL, Gunicorn, Nginx, Caddy), AWS EC2, Let's Encrypt HTTPS
- **AI:** Google Gemini (ixtiyoriy)
- **Testlar:** 133 ta avtomatik test (PostgreSQL ustida)

Arxitektura va reja: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Imkoniyatlar

- **Tovarlar:** rang × o'lcham variantlari (har birining o'z SKU, shtrix-kodi va qoldig'i), rasm, mavsum, kategoriya.
- **Ombor:** kirim, filiallar orasida ko'chirish, har bir o'zgarish jurnalga yoziladi, qoldiq manfiy bo'lmaydi.
- **Kassa:** shtrix-kod bilan qidirish, chek, takroriy so'rovda savdo ikki marta yozilmaydi.
- **Qaytarish:** faqat yaroqsiz tovar, 24 soat ichida, tasdiqlash huquqi bilan.
- **Aksiyalar:** muddatli chegirma barcha tovarlarga, kategoriyaga, **mavsumga** yoki tanlangan tovarlarga. Kassada avtomatik qo'llanadi, natijasi (aksiyadan oldin va aksiya davomida sotilgan dona) ko'rinadi.
- **Mijozlar va imtiyoz:** mijoz telefon raqami bilan, imtiyoz toifalari (masalan, VIP 10%). Aksiya bilan ustma-ust qo'shilmaydi, mijoz uchun foydalirog'i olinadi.
- **Bonus (keshbek):** har xariddan 3% bonus, 24 soatdan keyin ishlatiladi, chekning ko'pi bilan 35 foizi bonus bilan to'lanadi.
- **Tavsiyalar:** sotilmay qolish xavfi bo'lgan tovarlar (uzoq sotilmagan, sekin sotilayotgan, mavsumi tugayotgan), tavsiya qilingan chegirma va sabablari, bir bosishda aksiya yaratish. Ixtiyoriy Gemini xulosasi.
- **✨ Yordamchi:** HEMIS'dagi kabi yon panel. Xodimga dasturdan foydalanishni o'rgatadi: rolga mos tayyor mavzular (darhol, AI'siz) va erkin savollar (Gemini, javob yozilgan sari chiqadi). Faqat qo'llanmaga tayanadi, do'kon ma'lumotlarini bilmaydi va xodimning o'rniga ish qilmaydi.
- **Hisobot:** tushum, taxminiy yalpi foyda, qaytarishlar, qoldiq qiymati.
- **Rollar:** egasi, menejer, sotuvchi. Sotuvchi tannarxni ko'rmaydi, qo'lda chegirmasi cheklangan (standart 10%).

Barcha avtomatik chegirmalar va bonus narxni tannarxdan pastga tushirmaydi.

## Backendni lokal ishga tushirish

Talablar: Python 3.12+, PostgreSQL 16.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # qiymatlarni o'zgartiring, .env ni gitga qo'shmang
python manage.py migrate
python manage.py createsuperuser   # telefon raqami bilan
python manage.py runserver
```

API hujjati: http://localhost:8000/api/docs/

Docker bilan: `backend/.env` yarating, keyin loyiha ildizida `docker compose up --build`.

Serverga (AWS EC2) joylash: [docs/DEPLOY.md](docs/DEPLOY.md). Production'da Caddy (HTTPS) + Nginx + Gunicorn + PostgreSQL Docker konteynerlarida ishlaydi (`docker-compose.prod.yml`).

### AI: yordamchi va tavsiyalar xulosasi (ixtiyoriy)

"✨ Yordamchi"dagi erkin savollarga javobni va "Tavsiyalar" sahifasidagi qisqa xulosani Google Gemini yozadi. Buning uchun https://aistudio.google.com/apikey dan kalit oling va `backend/.env` ga qo'shing:

```bash
GEMINI_API_KEY=sizning-kalitingiz
GEMINI_MODEL=gemini-flash-lite-latest,gemini-3.5-flash-lite   # ixtiyoriy, vergul bilan zaxira model
ASSISTANT_HOURLY_LIMIT=30                                    # bitta xodim soatiga nechta savol bera oladi
```

Keyin backendni qayta ishga tushiring. Google eski modellarni vaqti-vaqti bilan yopadi: "model topilmadi" xabari chiqsa, kalitingizga ochiq modellarni https://aistudio.google.com da ko'ring va `GEMINI_MODEL` ni almashtiring. "Lite" modellar 1–2 soniyada javob beradi (oddiy flash 20 soniyadan ko'p). Kalit bo'lmasa ham yordamchining tayyor mavzulari va tavsiyalar to'liq ishlaydi: qaysi tovarga necha foiz chegirma berishni qoidalar hisoblaydi, Gemini faqat tayyor ro'yxatni umumlashtiradi. Gemini'ga faqat tovar nomlari va umumlashtirilgan raqamlar yuboriladi.

## Frontendni lokal ishga tushirish

Talablar: Node.js 20+. Backend `localhost:8000` da ishlayotgan bo'lishi kerak.

```bash
cd frontend
npm install
npm run dev
```

Brauzerda http://localhost:5173 oching. Dev rejimida `/api` so'rovlari avtomatik ravishda Django serveriga yo'naltiriladi.

Sinab ko'rish tartibi: Ro'yxatdan o'tish → Tovarlar → Yangi tovar (rang va o'lcham qo'shing) → Kirim → Kassa → Savdolar / Qoldiq → Aksiyalar → Mijozlar → Tavsiyalar.

## Demo ma'lumotlar

Taqdimot uchun tayyor do'kon (3 filial, 4 xodim, 10 tovar, 30 kunlik savdo, qaytarishlar, 6 mijoz va imtiyoz toifalari, bonuslar, aksiyalar, sotilmay turgan tovarlar, tovar rasmlari):

```bash
cd backend
python manage.py seed_demo          # qayta yaratish: seed_demo --reset, rasmsiz: --no-images
```

Tovar rasmlari birinchi marta Unsplash'dan (bepul litsenziya) yuklanadi va `backend/.cache/demo-images` ga saqlanadi: keyingi safar internet kerak emas. Internet bo'lmasa, demo rasmsiz yaratiladi.

Kirish: `+998 90 000 00 01` (egasi), `...02` (menejer), `...03` va `...04` (sotuvchilar), parol `Demo-12345`.
Kassada sinash uchun mijozlar: `90 123 45 01` (VIP 10%), `...02` va `...03` (Doimiy mijoz 5%), `...06` (Xodim 15%).
Taqdimot ssenariysi: [docs/DEMO.md](docs/DEMO.md).

## Testlar

```bash
cd backend
python manage.py test
```

133 ta avtomatik test: savdo, qoldiq, ko'chirish, qaytarish, hisobot, huquqlar, aksiya, imtiyoz, bonus, tavsiyalar va yordamchi (AI so'rovlari soxta javob bilan tekshiriladi).
Testlar PostgreSQL talab qiladi (qulflash va constraintlar tekshiriladi), `.env` dagi `DATABASE_URL` foydalanuvchisiga `CREATEDB` huquqi kerak.
