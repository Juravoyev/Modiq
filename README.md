# Modiq
Merchandise, warehouse, sales, and decision-support system for small-scale fashion retail.

Kichik kiyim, oyoq kiyim va sumka do'konlari uchun tovar (rang × o'lcham variantlari), ombor, kassa va qaror qabul qilishni qo'llab-quvvatlash tizimi.

Arxitektura va reja: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

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

Sinash uchun namunaviy do'kon (2 do'kon + ombor, 20 tovar, 90 kunlik savdolar; hammasi o'ylab topilgan):

```bash
python manage.py seed_demo          # qayta yaratish: --reset (faqat demo do'kon o'chiriladi)
```

Kirish: egasi `+998900000001`, sotuvchi `+998900000002`, parol `Demo-parol-2026`.

### Haftalik xulosa (ixtiyoriy)

Bosh sahifadagi "Haftalik xulosa" kartasi oxirgi 7 kun raqamlarini tizimning o'zi hisoblaydi, keyin Google Gemini
shu raqamlardan qisqa matn yozadi. Matn uchun `backend/.env` ga qo'shing (kalitni gitga va frontendga qo'ymang):

```
GEMINI_API_KEY=...            # https://aistudio.google.com dan
GEMINI_MODEL=gemini-3.6-flash # ixtiyoriy
```

Kalit bo'lmasa ham tizim ishlaydi: karta raqamlarni ko'rsatadi va matn "sozlanmagan" deb yozadi.

Docker bilan: `backend/.env` yarating, keyin loyiha ildizida `docker compose up --build`.

## Frontendni lokal ishga tushirish

Talablar: Node.js 20+. Backend `localhost:8000` da ishlayotgan bo'lishi kerak.

```bash
cd frontend
npm install
npm run dev
```

Brauzerda http://localhost:5173 oching. Dev rejimida `/api` so'rovlari avtomatik ravishda Django serveriga yo'naltiriladi.

Sinab ko'rish tartibi: demo do'kon bilan kiring yoki ro'yxatdan o'ting → Bosh sahifa → Aqlli tavsiyalar → Chegirmalar → Kassa → Savdolar (qaytarish) → Hisobotlar (CSV, chop etish) → Ko'chirish → Inventarizatsiya → Sozlamalar.

## Demo ma'lumotlar

Taqdimot uchun tayyor do'kon (3 filial, 4 xodim, 10 tovar, 30 kunlik savdo, qaytarishlar):

```bash
cd backend
python manage.py seed_presentation  # qayta yaratish: seed_presentation --reset
```

Kirish: `+998 90 000 00 01` (egasi), `...02` (menejer), `...03` va `...04` (sotuvchilar), parol `Demo-12345`.

Ikkala buyruq bir xil telefon raqamlardan foydalanadi, shuning uchun bir vaqtda faqat bittasi turadi:
`--reset` boshqasining demo do'konini ham o'chiradi (demo bo'lmagan do'konga tegmaydi).

Taqdimot ssenariysi: [docs/DEMO.md](docs/DEMO.md).

## Testlar

```bash
cd backend
python manage.py test
```

Testlar PostgreSQL talab qiladi (qulflash va constraintlar tekshiriladi), `.env` dagi `DATABASE_URL` foydalanuvchisiga `CREATEDB` huquqi kerak.
