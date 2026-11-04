# Modiq
Merchandise, warehouse, sales, and decision-support system for small-scale fashion retail.

Kichik kiyim, oyoq kiyim va sumka do'konlari uchun tovar (rang × o'lcham variantlari), ombor, kassa va qaror qabul qilishni qo'llab-quvvatlash tizimi.

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

### AI xulosasi (ixtiyoriy)

"Tavsiyalar" sahifasidagi qisqa xulosani Google Gemini yozadi. Buning uchun https://aistudio.google.com/apikey dan kalit oling va `backend/.env` ga qo'shing:

```bash
GEMINI_API_KEY=sizning-kalitingiz
GEMINI_MODEL=gemini-flash-latest,gemini-3.5-flash    # ixtiyoriy, vergul bilan zaxira model
```

Keyin backendni qayta ishga tushiring. Google eski modellarni vaqti-vaqti bilan yopadi: "model topilmadi" xabari chiqsa, kalitingizga ochiq modellarni https://aistudio.google.com da ko'ring va `GEMINI_MODEL` ni almashtiring. Kalit bo'lmasa ham tavsiyalar to'liq ishlaydi: qaysi tovarga necha foiz chegirma berishni qoidalar hisoblaydi, Gemini faqat tayyor ro'yxatni umumlashtiradi. Gemini'ga faqat tovar nomlari va umumlashtirilgan raqamlar yuboriladi.

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

Taqdimot uchun tayyor do'kon (3 filial, 4 xodim, 10 tovar, 30 kunlik savdo, qaytarishlar, 6 mijoz va imtiyoz toifalari, bonuslar, aksiyalar, sotilmay turgan tovarlar):

```bash
cd backend
python manage.py seed_demo          # qayta yaratish: seed_demo --reset
```

Kirish: `+998 90 000 00 01` (egasi), `...02` (menejer), `...03` va `...04` (sotuvchilar), parol `Demo-12345`.
Kassada sinash uchun mijozlar: `90 123 45 01` (VIP 10%), `...02` va `...03` (Doimiy mijoz 5%), `...06` (Xodim 15%).
Taqdimot ssenariysi: [docs/DEMO.md](docs/DEMO.md).

## Testlar

```bash
cd backend
python manage.py test
```

122 ta avtomatik test: savdo, qoldiq, ko'chirish, qaytarish, hisobot, huquqlar, aksiya, imtiyoz, bonus va tavsiyalar.
Testlar PostgreSQL talab qiladi (qulflash va constraintlar tekshiriladi), `.env` dagi `DATABASE_URL` foydalanuvchisiga `CREATEDB` huquqi kerak.
