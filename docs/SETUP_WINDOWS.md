# Modiq'ni Windows'da ishga tushirish

## 1. PostgreSQL o'rnatish (bir marta)

1. https://www.postgresql.org/download/windows/ sahifasidan PostgreSQL 16 o'rnatuvchisini yuklab oling.
2. O'rnatish paytida `postgres` foydalanuvchisi uchun parol so'raladi. Shu parolni eslab qoling. Port `5432` bo'lib qolsin.
3. Start menyusidan **SQL Shell (psql)** ni oching. Har bir savolga Enter bosing, oxirida `postgres` parolini kiriting.
4. Quyidagi ikki buyruqni kiriting (`modiq_parol` o'rniga o'zingizning parolingizni yozing, faqat harf va raqamlardan):

```sql
CREATE USER modiq WITH PASSWORD 'modiq_parol' CREATEDB;
CREATE DATABASE modiq OWNER modiq;
```

`CREATEDB` huquqi testlar o'z vaqtinchalik bazasini yaratishi uchun kerak.

## 2. Backend: venv va paketlar

PowerShell'da:

```powershell
cd D:\Django_projects\Modiq\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`activate` "running scripts is disabled" xatosini bersa, bir marta `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` buyrug'ini bajaring.

## 3. `.env` faylini yaratish

`.env` maxfiy sozlamalarni saqlaydi va gitga tushmaydi (`.gitignore` da bor). Uni namunadan nusxalab yarating:

```powershell
copy .env.example .env
```

Maxfiy kalitni yarating:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`backend\.env` faylini Notepad yoki VS Code'da ochib, shunday to'ldiring:

```
SECRET_KEY=<yuqoridagi buyruq chiqargan qator>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://modiq:modiq_parol@localhost:5432/modiq
CORS_ALLOWED_ORIGINS=http://localhost:5173
JWT_ACCESS_MINUTES=60
JWT_REFRESH_DAYS=14
LOG_LEVEL=INFO
```

`DATABASE_URL` tuzilishi: `postgres://FOYDALANUVCHI:PAROL@HOST:PORT/BAZA`. Parolda `@`, `:`, `/`, `#` belgilari bo'lsa, ular URL'ni buzadi. Shuning uchun parolni faqat harf va raqamlardan tuzing.

## 4. Bazani tayyorlash va serverni ishga tushirish

```powershell
python manage.py migrate
python manage.py test
python manage.py createsuperuser
python manage.py runserver
```

* `migrate` jadvallarni yaratadi.
* `test` 74 ta testni ishga tushiradi, oxirida `OK` chiqishi kerak.
* `createsuperuser` admin panel uchun foydalanuvchi yaratadi. Telefonni `+998901234567` ko'rinishida kiriting.
* Tekshirish: http://localhost:8000/api/docs/ (API) va http://localhost:8000/admin/ (admin panel).

## 5. Frontend

Yangi PowerShell oynasida (backend ishlab turgan bo'lishi kerak):

```powershell
cd D:\Django_projects\Modiq\frontend
npm install
npm run dev
```

Brauzerda http://localhost:5173 ni oching. Ro'yxatdan o'ting, so'ng: Tovarlar → Yangi tovar → Kirim → Kassa.

## Tez-tez uchraydigan xatolar

| Xato | Sabab va yechim |
|---|---|
| `connection refused ... 5432` | PostgreSQL ishlamayapti. Windows Services'da `postgresql-x64-16` ni ishga tushiring. |
| `password authentication failed for user "modiq"` | `.env` dagi parol SQL'da yozgan parolingizga mos emas. |
| `database "modiq" does not exist` | 1-bosqichdagi `CREATE DATABASE` bajarilmagan. |
| `ImproperlyConfigured: Set the SECRET_KEY` | `.env` fayli `backend` papkasida emas yoki `SECRET_KEY` bo'sh. |
| `permission denied to create database` (testda) | `ALTER USER modiq CREATEDB;` buyrug'ini bajaring. |
| `npm` topilmadi | Node.js 20+ o'rnating: https://nodejs.org |
