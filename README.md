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

Docker bilan: `backend/.env` yarating, keyin loyiha ildizida `docker compose up --build`.

## Frontendni lokal ishga tushirish

Talablar: Node.js 20+. Backend `localhost:8000` da ishlayotgan bo'lishi kerak.

```bash
cd frontend
npm install
npm run dev
```

Brauzerda http://localhost:5173 oching. Dev rejimida `/api` so'rovlari avtomatik ravishda Django serveriga yo'naltiriladi.

Sinab ko'rish tartibi: Ro'yxatdan o'tish → Tovarlar → Yangi tovar (rang va o'lcham qo'shing) → Kirim → Kassa → Savdolar / Qoldiq.

## Demo ma'lumotlar

Taqdimot uchun tayyor do'kon (3 filial, 4 xodim, 10 tovar, 30 kunlik savdo, qaytarishlar):

```bash
cd backend
python manage.py seed_demo          # qayta yaratish: seed_demo --reset
```

Kirish: `+998 90 000 00 01` (egasi), `...02` (menejer), `...03` va `...04` (sotuvchilar), parol `Demo-12345`.
Taqdimot ssenariysi: [docs/DEMO.md](docs/DEMO.md).

## Testlar

```bash
cd backend
python manage.py test
```

Testlar PostgreSQL talab qiladi (qulflash va constraintlar tekshiriladi), `.env` dagi `DATABASE_URL` foydalanuvchisiga `CREATEDB` huquqi kerak.
