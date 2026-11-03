# Modiq arxitekturasi

## 1. Umumiy ko'rinish

```
React + TS (PWA)  ──HTTP/JSON, JWT──▶  Django + DRF  ──ORM──▶  PostgreSQL
        (frontend/, keyingi qadam)        (backend/)
```

Backend modullari (`backend/apps/`):

| App | Vazifasi |
|---|---|
| `common` | Abstract modellar, tenant permission, tenantga cheklangan maydonlar, pagination (`?page_size=`) |
| `accounts` | Telefon+parol bilan foydalanuvchi, Business (tenant), Branch (filial), Membership (rol) |
| `catalog` | Kategoriya, brend, mavsum, rang, o'lcham, Product (model), ProductVariant (rang×o'lcham = SKU) |
| `inventory` | Stock (filial×variant qoldig'i), StockMovement (jurnal), Receipt (kirim), Transfer (ko'chirish) |
| `sales` | Sale, SaleLine (kassa), SaleReturn (qaytarish) |
| `insights` | Sotilmay qolish xavfi qoidalari, sotuv sur'ati, sozlanadigan chegaralar (RiskSettings) |
| `discounts` | Muddatli chegirmalar: qoralama → tasdiq → kassada avtomatik qo'llash, tarix o'chirilmaydi |
| `reports` | Dashboard, savdo/tovar/qoldiq/xavf hisobotlari, CSV eksport, chegirma natijasi |

Modullar orasidagi bog'liqlik bir tomonlama: `catalog` hech qaysi yuqori modulni import qilmaydi
(`catalog/tests/test_dependencies.py` tekshiradi). `sales` → `discounts` → `catalog`, `reports` esa
`sales`, `discounts` va `insights` dan o'qiydi. Chegirma natijasi `reports` da hisoblanadi, aks holda
`sales` ↔ `discounts` aylana bog'liqligi paydo bo'lardi.

## 2. Asosiy qarorlar va sabablari

1. **Qoldiq variantda, mahsulotda emas.** `Stock(branch, variant, quantity)`. Mahsulotning umumiy qoldig'i variantlar yig'indisi sifatida hisoblanadi, alohida saqlanmaydi. Shu sababli ikki raqam bir-biridan farq qilib qolmaydi.
2. **Qoldiq faqat `inventory/services.py::change_stock` orqali o'zgaradi.** U qatorni `select_for_update` bilan qulflaydi, manfiy qoldiqqa yo'l qo'ymaydi va `StockMovement` jurnaliga yozadi. Bazada ham `quantity >= 0` CHECK constraint bor.
3. **Hujjatlar holat mashinasi.** Kirim: `draft → confirmed | cancelled`. Ko'chirish: `draft → sent → received`, `draft|sent → cancelled` (yo'ldagi tovar jo'natuvchiga qaytadi). Har bir o'tishda hujjat qatori qulflanadi va holati qayta tekshiriladi, shuning uchun ikki marta bosish qoldiqni ikki marta o'zgartirmaydi.
4. **Savdo idempotent.** Kassa har bir savdoga yangi `idempotency_key` (UUID) yuboradi. `(business, idempotency_key)` unikal. Internet uzilib so'rov qayta kelsa, eski savdo qaytariladi (HTTP 200), yangisi yaratilmaydi.
5. **Narx va tannarx savdo paytida yoziladi** (`SaleLine.unit_price`, `unit_cost`). Keyin mahsulot narxi o'zgarsa ham eski savdolar va foyda hisoboti o'zgarmaydi.
6. **Tannarxdan past narx.** Sotuvchi bunday savdoni yakunlay olmaydi. Menejer/egasi faqat `allow_below_cost: true` bilan ochiq tasdiqlasa o'tadi, qator `below_cost=true` deb belgilanadi.
7. **Tenant ajratilishi.** Har bir modelda `business` FK bor. `IsBusinessMember` permission `request.business`ni o'rnatadi, barcha querysetlar shu bilan filtrlanadi. Kiruvchi id'lar `BusinessScopedPKField` orqali tekshiriladi: boshqa biznesning id'si "topilmadi" bo'ladi.
8. **Rollar.** `owner` va `manager` barcha filiallarni ko'radi va katalog/kirim/ko'chirishni boshqaradi. `cashier` faqat biriktirilgan filiallarda ko'radi va sotadi, tannarx va yalpi foydani ko'rmaydi.
9. **MVP soddaligi.** Bitta foydalanuvchi = bitta biznes (`Membership` OneToOne). Bir nechta biznes kerak bo'lsa, keyin `X-Business` header bilan kengaytiriladi.
10. **Pul.** `Decimal(14,2)`, valyuta UZS. Float ishlatilmaydi.
11. **Chegirma narxini server hisoblaydi.** Kassa `/api/discounts/active/` dan narxni faqat ko'rsatish uchun oladi. Savdo yaratilganda server bugungi tasdiqlangan chegirmani o'zi topadi va `SaleLine.discount` ga bog'laydi. Chegirma yaratilganda narx va tannarx nusxalanadi, tannarxdan past chegirmani faqat menejer/egasi `allow_below_cost` bilan tasdiqlaydi. Bir variantga bir vaqtda ikkita tasdiqlangan chegirma bo'lmaydi.
12. **Hisobotlar bir xil shaklda.** `{title, date_from, date_to, columns, rows, totals, formulas}`. Frontend bitta jadval komponenti bilan hammasini ko'rsatadi, `?export=csv` xuddi shu ma'lumotni CSV qilib beradi. PDF uchun alohida kutubxona ishlatilmaydi: brauzerning chop etish oynasi (print CSS) orqali PDF saqlanadi.
13. **Til modeli faqat matn yozadi.** Haftalik xulosada barcha raqamlar `reports/summary.py::weekly_facts` da bazadan hisoblanadi. Gemini'ga faqat shu JSON yuboriladi va undan yangi raqam yoki prognoz o'ylab topmaslik so'raladi. Kalit faqat backend `.env` da, so'rov `x-goog-api-key` sarlavhasi bilan standart `urllib` orqali yuboriladi (qo'shimcha kutubxona yo'q). Kalit bo'lmasa yoki xizmat javob bermasa, sahifa raqamlarni baribir ko'rsatadi.

## 3. API (hozir mavjud)

Hujjat: `/api/docs/` (Swagger), sxema: `/api/schema/`.

| Endpoint | Izoh |
|---|---|
| `POST /api/auth/register/` | Egasi + biznes + birinchi filial |
| `POST /api/auth/login/`, `POST /api/auth/refresh/` | JWT (telefon + parol) |
| `GET /api/auth/me/` | Joriy foydalanuvchi, rol, filiallar |
| `/api/auth/branches/` | Filiallar (yozish: menejer). O'chirilmaydi, `is_active=false` bilan yopiladi; oxirgi faol filialni yopib bo'lmaydi |
| `/api/auth/members/` | Xodimlar: ko'rish menejer, qo'shish va `PATCH` (rol, filiallar, holat, parol, `can_approve_returns`) faqat egasi |
| `/api/catalog/{categories,brands,seasons,colors,sizes}/` | Ma'lumotnomalar |
| `/api/catalog/products/` | Tovarlar; `color_ids`+`size_ids` bilan variantlar matritsasi yaratiladi; `total_stock` |
| `POST /api/catalog/products/{id}/generate-variants/` | Yangi rang/o'lcham qo'shish |
| `POST`/`DELETE /api/catalog/products/{id}/image/` | Tovar rasmi (multipart). WebP, eng katta tomoni 1200px gacha siqiladi |
| `/api/catalog/variants/?search=` | Kassa qidiruvi (SKU, shtrix-kod, nom), `stock` bilan |
| `GET /api/inventory/stock/?branch=&low=true` | Qoldiqlar, kam qolganlar |
| `GET /api/inventory/movements/` | Ombor harakatlari tarixi |
| `/api/inventory/receipts/` + `/confirm/`, `/cancel/` | Kirim |
| `/api/inventory/transfers/` + `/send/`, `/receive/`, `/cancel/` | Ko'chirish |
| `/api/sales/` | `POST` savdoni yakunlash, `GET` tarix (`returned_quantity`, `returned_total`, `return_deadline` bilan) |
| `POST /api/sales/{id}/return/` | Sotuvga qaytadigan tovar: darhol tasdiqlanadi, qoldiq tiklanadi, summa proporsional qaytariladi |
| `/api/sales/returns/` + `/approve/`, `/reject/` | Qaytarishlar ro'yxati; yaroqsiz tovarni qaytarish (`kind=defective`, 24 soat ichida, tasdiq bilan, hisobdan chiqariladi) |
| `GET /api/sales/dashboard/?days=7\|30\|90&branch=` | Hisobot: tushum, foyda, qaytarishlar, qoldiq qiymati, sotilmayotgan tovarlar (egasi/menejer) |
| `/api/inventory/counts/` + `/apply/`, `/cancel/` | Inventarizatsiya: sanoq kiritiladi, tasdiqlanganda qoldiq tenglashtiriladi |
| `PATCH /api/auth/members/{id}/` | Xodim roli, filiallari, faolligi, paroli, qaytarishni tasdiqlash huquqi |
| `GET /api/insights/risks/?branch=&type=&level=` | Xavfli variantlar, har birida `reason` va `action` |
| `GET/PATCH /api/insights/settings/` | Xavf qoidalari chegaralari |
| `GET /api/reports/dashboard/?branch=` | Bugungi tushum, savdolar, qoldiq, kam qolganlar, ogohlantirishlar, `formulas` |
| `/api/discounts/?state=` + `/approve/`, `/cancel/` | Chegirmalar (menejer/egasi). `state`: active, scheduled, draft, finished, cancelled |
| `GET /api/discounts/active/` | Bugun amaldagi chegirma narxlari (kassa uchun, tannarxsiz) |
| `GET /api/reports/{sales,products,stock,slow,seasonal}/?branch=&date_from=&date_to=&group=` | Hisobotlar; `&export=csv` bilan CSV fayl |
| `GET /api/reports/discounts/{id}/results/` | Chegirma davri va undan oldingi teng davr sotuvi |
| `GET/POST /api/reports/weekly-summary/?branch=` | Haftalik faktlar (GET) va ular asosidagi qisqa matn (POST, 1 soat keshlanadi) |

## 4. Implementatsiya ketma-ketligi

1. ✅ Backend yadrosi: auth, filiallar, katalog, kirim, qoldiq, ko'chirish, savdo + testlar.
2. ✅ Frontend skeleti: Vite + React + TS, login/ro'yxatdan o'tish, layout (desktop yon menyu, mobil pastki menyu), Kassa, Tovarlar, Kirim, Qoldiq, Savdolar.
3. ✅ Ko'chirish sahifasi, xodimlar va filiallar sahifasi, tovarni tahrirlash, mahsulot rasmlari.
4. ✅ Inventarizatsiya. Savdoni qaytarish: sotuvga qaytadigan tovar (qoldiq tiklanadi) va yaroqsiz tovar (24 soat, tasdiqlash huquqi, hisobdan chiqarish).
5. ✅ Aqlli tavsiyalar: 4 qoida + "Nega bu tavsiya berildi?" izohi, sozlanadigan chegaralar.
6. ✅ Dashboard (formulalar bilan) va davr bo'yicha hisobot (tushum, foyda, qaytarishlar, qoldiq qiymati, sotilmayotgan tovarlar). Namunaviy ma'lumot: `python manage.py seed_demo` yoki taqdimot uchun `python manage.py seed_presentation`.
7. ✅ Chegirma boshqaruvi (muddatli, tasdiqlash bilan, tarix, natijani kuzatish).
8. ✅ Hisobotlar: kunlik/haftalik/oylik savdo, mahsulotlar bo'yicha, qoldiq, kam sotiladigan, mavsumiy; CSV, PDF (chop etish orqali).
9. Production (oxirida): Nginx, HTTPS, backup, CI.
10. ✅ Til modeli bilan haftalik xulosa (faqat backend orqali). Ixtiyoriy keyingi qadam: nakladnoy rasmini o'qish.

## 5. Test rejasi (talab 7-bo'lim)

| # | Ssenariy | Holat |
|---|---|---|
| 1 | Savdo qoldiqni kamaytiradi | ✅ `sales/tests` |
| 2 | Takroriy savdo ikki marta kamaytirmaydi | ✅ idempotency testi |
| 3 | Qoldiq yetmasa savdo bloklanadi, hech narsa o'zgarmaydi | ✅ + parallel oxirgi dona testi |
| 4 | Kirim takroran qo'llanmaydi | ✅ `inventory/tests` |
| 5 | Ko'chirish to'g'ri ishlaydi (ikki marta jo'natish/qabul yo'q, bekor qilish qaytaradi) | ✅ |
| 6 | Bir biznes boshqasining ma'lumotini ko'ra/ishlata olmaydi | ✅ `TenantIsolationTests` |
| 7 | Chegirma va narx hisob-kitobi, tannarxdan past narx | ✅ `sales/tests`, `discounts/tests` |
| 8 | Dashboard va hisobot raqamlari haqiqiy savdo va qaytarishlarga mos, CSV | ✅ `reports/tests`, `sales/tests/test_dashboard.py` |
| 9 | Qaytarish: sotilganidan ko'p qaytarib bo'lmaydi, summa proporsional; yaroqsiz tovar: muddat, tasdiqlash huquqi, qoldiqqa qaytmaydi | ✅ `sales/tests/test_returns.py` |
| 10 | Inventarizatsiya ikki marta qo'llanmaydi, farq jurnalga yoziladi | ✅ `inventory/tests/test_stock_count.py` |
| 11 | Xavf qoidalari: chegara, sozlash, ma'lumot yetarli bo'lmaganda sur'at yo'q | ✅ `insights/tests` |
| 12 | Demo ma'lumotda qoldiq = jurnal yig'indisi | ✅ `accounts/tests/test_seed_demo.py` |
| 13 | Chegirma: ustma-ust tushmaydi, muddati o'tgani qo'llanmaydi, kassir tasdiqlay olmaydi | ✅ `discounts/tests` |
| 14 | Katalog yuqori modullarga bog'liq emas | ✅ `catalog/tests/test_dependencies.py` |
| 15 | Haftalik xulosa: faktlar haqiqiy savdodan, kalitsiz/xatoda tushunarli javob, kalit URL da emas | ✅ `reports/tests/test_summary.py` |
| 16 | Xodim va filial boshqaruvi huquqlari | ✅ `accounts/tests/test_staff_branches.py` |

## 6. Frontend tuzilishi (`frontend/src/`)

| Papka | Vazifasi |
|---|---|
| `api/client.ts` | `fetch` o'rami: JWT, 401 da token yangilash, DRF xatolarini o'zbekcha xabarga aylantirish |
| `api/types.ts` | Backend javoblari turlari |
| `auth/AuthContext.tsx` | Joriy foydalanuvchi, tanlangan filial, login/logout |
| `components/` | Layout, Logo (izometrik kub), Receipt (chek), umumiy UI (Loading, Empty, ErrorBox, Field, Pagination, StockBadge) |
| `pages/` | Login, Register, Kassa, Hisobot, Tovarlar, Yangi tovar, Tovarni tahrirlash, Kirim, Ko'chirish, Qoldiq, Savdolar, Qaytarish, Xodimlar, Filiallar, "Yana" (telefon menyusi) |
| `styles/global.css` | Dizayn tokenlari va komponent klasslari |

Qo'shimcha kutubxona faqat `react-router-dom` (sahifalar orasida yurish). Holat boshqaruvi uchun alohida kutubxona ishlatilmagan.

Ma'lum cheklovlar (texnik qarz):
* JWT `localStorage` da saqlanadi. Production'dan oldin httpOnly cookie'ga o'tkazishni ko'rib chiqish kerak.
* PWA hozircha faqat manifest bilan, offline ishlash (service worker) yo'q.
* Frontend uchun avtomatik testlar hali yo'q (qo'lda va Playwright skript bilan tekshirilgan).

## 7. Aqlli tavsiyalar qoidalari (`apps/insights/engine.py`)

Har bir do'kon filiali va variant uchun (omborlar savdo qilmagani uchun tahlil qilinmaydi, lekin ko'chirish tavsiyasida qatnashadi):

| Qoida | Shart | Daraja |
|---|---|---|
| Sotilmay qolish | Qoldiq > 0 va oxirgi sotuvdan (sotilmagan bo'lsa, tovar kelgan kundan) beri ≥ `no_sale_days` kun | 2× chegaradan oshsa yuqori, aks holda o'rta |
| Ortiqcha zaxira | Sur'at ishonchli (davrda ≥ `min_sales_for_velocity` dona) va qoldiq / sur'at > `overstock_cover_days` | 2× chegaradan oshsa yuqori |
| Mavsumiy | Mavsum tugashiga ≤ `season_warning_days` kun va kutilgan sotuvdan ko'p qoldiq qoladi; mavsum tugagan va sotuv to'xtagan bo'lsa past | qoldiqning yarmidan ko'pi qolsa yuqori |
| Qayta to'ldirish | Qoldiq ≤ minimal va davrda sotuv bo'lgan; boshqa filialda ortiqcha bo'lsa, ko'chirish taklif qilinadi | tugagan bo'lsa yuqori |

Sotuv sur'ati = davrdagi sof sotuv (qaytarishlarsiz) / davr kunlari. Ma'lumot yetarli bo'lmasa "ma'lumot yetarli emas" deb ko'rsatiladi.
