# Modiq arxitekturasi (2-bosqich rejasi)

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
| `sales` | Sale, SaleLine (kassa) |

Keyingi bosqichlarda: `insights` (sotilmay qolish xavfi), `pricing` (chegirmalar), `reports`.

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
| `/api/sales/` | `POST` savdoni yakunlash, `GET` tarix (`returned_quantity`, `return_deadline` bilan) |
| `/api/sales/returns/` + `/approve/`, `/reject/` | Yaroqsiz tovarni qaytarish (24 soat ichida) |
| `GET /api/sales/dashboard/?days=7\|30\|90&branch=` | Hisobot: tushum, foyda, qaytarishlar, qoldiq qiymati, sotilmayotgan tovarlar (egasi/menejer) |

## 4. Implementatsiya ketma-ketligi

1. ✅ Backend yadrosi: auth, filiallar, katalog, kirim, qoldiq, ko'chirish, savdo + testlar.
2. ✅ Frontend skeleti: Vite + React + TS, login/ro'yxatdan o'tish, layout (desktop yon menyu, mobil pastki menyu), Kassa, Tovarlar, Kirim, Qoldiq, Savdolar.
3. ✅ Ko'chirish sahifasi, xodimlar va filiallar sahifasi, tovarni tahrirlash.
4. ✅ Savdoni qaytarish (faqat yaroqsiz tovar, 24 soat, tasdiqlash huquqi, hisobdan chiqarish). ⏭ Qoldiqni tekshirish (inventarizatsiya tuzatishi).
5. Aqlli tavsiyalar: sotilmay qolish xavfi qoidalari + "Nega bu tavsiya berildi?" izohi, sozlanadigan chegaralar.
6. Chegirma boshqaruvi (muddatli, tasdiqlash bilan, tarix).
7. ✅ Dashboard: tushum, "taxminiy yalpi foyda" (sof foyda emas), qaytarishlar, qoldiq qiymati, sotilmayotgan tovarlar. ⏭ CSV/PDF eksport.
8. Production: Nginx, HTTPS, backup, CI.

## 5. Test rejasi (talab 7-bo'lim)

| # | Ssenariy | Holat |
|---|---|---|
| 1 | Savdo qoldiqni kamaytiradi | ✅ `sales/tests` |
| 2 | Takroriy savdo ikki marta kamaytirmaydi | ✅ idempotency testi |
| 3 | Qoldiq yetmasa savdo bloklanadi, hech narsa o'zgarmaydi | ✅ + parallel oxirgi dona testi |
| 4 | Kirim takroran qo'llanmaydi | ✅ `inventory/tests` |
| 5 | Ko'chirish to'g'ri ishlaydi (ikki marta jo'natish/qabul yo'q, bekor qilish qaytaradi) | ✅ |
| 6 | Bir biznes boshqasining ma'lumotini ko'ra/ishlata olmaydi | ✅ `TenantIsolationTests` |
| 7 | Chegirma va narx hisob-kitobi, tannarxdan past narx | ✅ |
| 8 | Hisobotlar haqiqiy ma'lumotlarga mos | ✅ `sales/tests/test_dashboard.py` |
| 9 | Qaytarish: muddat, sotilganidan ko'p qaytarib bo'lmaydi, tasdiqlash huquqi, qoldiqqa qaytmaydi | ✅ `sales/tests/test_returns.py` |
| 10 | Xodim va filial boshqaruvi huquqlari | ✅ `accounts/tests/test_staff_branches.py` |

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
