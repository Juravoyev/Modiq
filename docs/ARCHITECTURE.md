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
| `customers` | Customer (telefon bilan), CustomerGroup (imtiyoz toifasi: doimiy chegirma foizi), BonusTransaction (bonus jurnali) |
| `pricing` | Promotion (muddatli aksiya: barcha tovar, kategoriya, mavsum yoki tanlangan tovarlar), PricingSettings, narx hisoblash (`services.price_cart`) |

| `insights` | Sotilmay qolish xavfi: qoidalar bo'yicha tavsiya (`services.build_recommendations`), InsightSettings (chegaralar), Dismissal (rad etilgan tavsiya), Gemini xulosasi (`ai.py`) |

| `assistant` | "✨ Yordamchi": dasturdan foydalanishni o'rgatadi. Qo'llanma (`guide.py`), rolga mos tayyor mavzular, erkin savol (stream) |

`common/llm.py` — til modeli bilan aloqa (hozir Gemini; keyin OpenRouter ham shu yerga qo'shiladi): zaxira modellar, tushunarli xatolar, `generate` va `stream`.

Keyingi bosqichlarda: `reports` (CSV/PDF eksport).

**Yordamchi** (`assistant/`). Bilim manbai — `guide.py` dagi qo'llanma (har bir mavzu: sarlavha, qadamlar, rol, sahifa havolasi). Dasturda tugma yoki sahifa o'zgarsa, qo'llanma ham yangilanishi kerak.
1. Tayyor mavzular xodimning roliga qarab beriladi (sotuvchi, menejer, egasi, qaytarishni tasdiqlovchi) va AI'siz, darhol ko'rsatiladi.
2. Erkin savolga AI faqat shu xodimga ruxsat etilgan qo'llanma qismlariga tayanib javob beradi. Qo'llanmada yo'q narsani o'ylab topmaydi, ruxsat etilmagan ish haqida "egasi yoki menejer bajaradi" deydi, joriy sahifani biladi.
3. Do'kon ma'lumotlari (savdo, qoldiq, mijozlar) AI'ga yuborilmaydi; bunday savolga raqam aytmaydi, qaysi bo'limda ko'rishni aytadi. Xodimning o'rniga ish qilmaydi, faqat qadamlarni tushuntiradi.
4. Javob bo'lak-bo'lak (`StreamingHttpResponse`, `text/plain`) keladi; xato javob boshlanishidan oldin JSON bilan qaytadi. Bir xil birinchi savol 24 soat keshlanadi, bitta xodim soatiga `ASSISTANT_HOURLY_LIMIT` (30) tagacha savol beradi.

**Sotilmay qolish xavfi** (`insights/services.py`). Qarorni qoidalar chiqaradi, har bir tavsiyada sababi matn bilan beriladi:
1. Yuqori xavf: `no_sale_days` (60) kun bitta ham sotilmagan → `high_discount` (30%).
2. O'rta xavf: oxirgi 30 kundagi tezlikda qoldiq `cover_days_medium` (90) kundan ko'proqqa yetadi → 20%. Past xavf: `cover_days_low` (60) kun → 10%.
3. Mavsum: tovar mavsumi `season_end_days` (30) kun ichida tugaydi va qoldiq ulgurmaydi yoki mavsum tugagan → `season_discount` (20%). "Butun yil" mavsumi baholanmaydi.
4. Bir nechta qoida to'g'ri kelsa, eng katta chegirma olinadi. Chegirma narxni tannarxdan pastga tushirmaydi (eng kam foydali variant bo'yicha cheklanadi). Omborga `min_age_days` (14) kundan kam oldin kelgan tovar baholanmaydi. Faol aksiyasi bor tovarga yangi aksiya taklif qilinmaydi.
5. "Aksiya yaratish" tavsiya qilingan tovar va foiz bilan aksiya formasini ochadi (`source=recommendation`). Aksiya natijasi (`effect`): aksiya davomida va undan oldingi xuddi shuncha kunda sotilgan dona.
6. Gemini (`GEMINI_API_KEY`, ixtiyoriy) faqat tayyor ro'yxatdan qisqa xulosa yozadi, foizlarni o'zgartirmaydi. Unga tovar nomlari va umumlashtirilgan raqamlar yuboriladi (mijozlar, xodimlar, do'kon nomi yuborilmaydi). Javob 1 soat keshlanadi. `GEMINI_MODEL` da vergul bilan zaxira modellar beriladi: model band (503), eskirgan (404) yoki sekin bo'lsa, keyingisi sinaladi. Kalit bo'lmasa yoki Gemini javob bermasa, tavsiyalar baribir ishlaydi.

**Narx hisoblash qoidalari** (`pricing/services.py::price_cart`). Kassaning oldindan hisobi (`POST /api/sales/quote/`) ham, savdoni yakunlash ham shu bitta funksiyadan o'tadi, shuning uchun ekrandagi va bazadagi summa bir xil qoidalar bilan hisoblanadi:
1. Tovarga to'g'ri keladigan faol aksiyalardan mijoz uchun eng foydalisi olinadi, aksiyalar ustma-ust qo'shilmaydi.
2. Mijoz imtiyozi (toifa foizi) ham aksiya bilan qo'shilmaydi: har bir qatorda ikkisidan foydalirog'i olinadi.
3. Avtomatik chegirma narxni tannarxdan pastga tushirmaydi.
4. Sotuvchining qo'lda beradigan chegirmasi `cashier_max_discount_percent` bilan cheklangan (standart 10%). Egasi va menejerda chegara yo'q, lekin tannarxdan past sotish uchun alohida tasdiq kerak.
5. Bonus (keshbek): mijoz pul bilan to'lagan summaning `bonus_percent` foizi (standart 3%) yig'iladi, 1 ball = 1 so'm. Chekning ko'pi bilan `bonus_max_share_percent` foizi (standart 35%) bonus bilan to'lanadi, bonus ham tannarxdan pastga tushirmaydi va qatorlarga bo'sh joyi ulushida taqsimlanadi (`SaleLine.bonus_amount`). Balans saqlanmaydi, `BonusTransaction` jurnalidan hisoblanadi. Yangi bonus 24 soatdan (qaytarish muddati) keyin ishlatiladi, shu sababli qaytarishda bekor qilinadigan bonus hali sarflanmagan bo'ladi. Savdoda mijoz qatori qulflanadi: bitta bonusni ikki kassada ikki marta ishlatib bo'lmaydi. Tasdiqlangan qaytarishda bonus bilan to'langan ulush balansga qaytadi, yig'ilgan bonus ulushi bekor qilinadi (balans manfiyga tushmaydi).
6. Qo'llangan aksiya yoki imtiyoz, uning nomi va summasi `SaleLine` ga yozib qo'yiladi: aksiya keyin o'zgarsa ham eski chek o'zgarmaydi. Savdoda ishlatilgan aksiyani o'chirib bo'lmaydi, faqat to'xtatiladi.

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
| `POST /api/sales/quote/` | Savatning yakuniy narxi (aksiya, chegirma). Hech narsa saqlanmaydi |
| `/api/pricing/promotions/?status=` + `/stop/`, `/resume/` | Aksiyalar (yozish: menejer), natijasi bilan (`sales_count`, `units_sold`, `discount_given`) |
| `/api/pricing/settings/` | Chegirma sozlamalari (yozish: menejer) |
| `/api/customers/?phone=&search=` | Mijozlar (qo'shish: hamma, toifani belgilash va o'chirish: menejer), `purchases_count`, `total_spent` |
| `/api/customers/groups/` | Imtiyoz toifalari, 0–50% (yozish: menejer) |
| `GET /api/insights/recommendations/?branch=` | Sotilmay qolish xavfi bo'lgan tovarlar, tavsiya qilingan chegirma va sabablari (egasi/menejer) |
| `POST /api/insights/recommendations/summary/?refresh=1` | Gemini xulosasi (503 `ai_not_configured`/`ai_unavailable` — tavsiyalar baribir ishlaydi) |
| `POST /api/insights/recommendations/dismiss/` | Tavsiyani 30 kunga yashirish |
| `/api/insights/settings/` | Qoidalar chegaralari |
| `GET /api/assistant/topics/` | Yordamchining rolga mos tayyor mavzulari, `ai_configured` |
| `POST /api/assistant/ask/` | Erkin savol (`question`, `page`, `history`). Javob `text/plain` stream; 429 `assistant_limit`, 503 `ai_*` |
| `GET /api/customers/{id}/bonus/` | Mijozning bonus tarixi; ro'yxatda `bonus_available`, `bonus_pending` |
| `/api/sales/` | `POST` savdoni yakunlash, `GET` tarix (`returned_quantity`, `return_deadline` bilan) |
| `/api/sales/returns/` + `/approve/`, `/reject/` | Yaroqsiz tovarni qaytarish (24 soat ichida) |
| `GET /api/sales/dashboard/?days=7\|30\|90&branch=` | Hisobot: tushum, foyda, qaytarishlar, qoldiq qiymati, sotilmayotgan tovarlar (egasi/menejer) |

## 4. Implementatsiya ketma-ketligi

1. ✅ Backend yadrosi: auth, filiallar, katalog, kirim, qoldiq, ko'chirish, savdo + testlar.
2. ✅ Frontend skeleti: Vite + React + TS, login/ro'yxatdan o'tish, layout (desktop yon menyu, mobil pastki menyu), Kassa, Tovarlar, Kirim, Qoldiq, Savdolar.
3. ✅ Ko'chirish sahifasi, xodimlar va filiallar sahifasi, tovarni tahrirlash.
4. ✅ Savdoni qaytarish (faqat yaroqsiz tovar, 24 soat, tasdiqlash huquqi, hisobdan chiqarish). ⏭ Qoldiqni tekshirish (inventarizatsiya tuzatishi).
5. ✅ Aqlli tavsiyalar: sotilmay qolish xavfi qoidalari (mavsum bilan) + "Nega?" izohi, sozlanadigan chegaralar, Gemini xulosasi.
6. ✅ Chegirma boshqaruvi: muddatli aksiyalar (mavsum, kategoriya, tovar), natijasi, mijoz imtiyozi, bonus (keshbek), sotuvchi chegarasi.
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
| 11 | Aksiya: eng foydalisi, ustma-ust emas, tannarxdan past emas, muddat, qamrov (mavsum/kategoriya/tovar), sotuvchi chegarasi | ✅ `pricing/tests/test_promotions.py` |
| 12 | Imtiyoz: aksiya bilan qo'shilmaydi, tannarxdan past emas, toifani faqat menejer beradi | ✅ `customers/tests/test_customers.py` |
| 13 | Bonus: 3% pul bilan to'langanidan, 35% chegara, tannarxdan past emas, 24 soat kutish, takroriy so'rovda ikki marta yozilmaydi, qaytarishda qaytarish/bekor qilish | ✅ `customers/tests/test_bonus.py` |
| 14 | Tavsiyalar: yuqori/o'rta/past xavf, mavsum, yangi tovar baholanmaydi, tannarx chegarasi, faol aksiya, rad etish, Gemini (soxta javob bilan) | ✅ `insights/tests/test_recommendations.py` |
| 15 | Yordamchi: rolga mos mavzular, qo'llanma va sahifa AI'ga beriladi, do'kon ma'lumoti yuborilmaydi, kesh, zaxira model, soatlik limit | ✅ `assistant/tests/test_assistant.py` |

## 6. Frontend tuzilishi (`frontend/src/`)

| Papka | Vazifasi |
|---|---|
| `api/client.ts` | `fetch` o'rami: JWT, 401 da token yangilash, DRF xatolarini o'zbekcha xabarga aylantirish |
| `api/types.ts` | Backend javoblari turlari |
| `auth/AuthContext.tsx` | Joriy foydalanuvchi, tanlangan filial, login/logout |
| `components/` | Layout, Logo (izometrik kub), Receipt (chek), umumiy UI (Loading, Empty, ErrorBox, Field, Pagination, StockBadge) |
| `pages/` | Login, Register, Kassa, Hisobot, Tovarlar, Yangi tovar, Tovarni tahrirlash, Kirim, Ko'chirish, Qoldiq, Savdolar, Qaytarish, Mijozlar, Aksiyalar, Tavsiyalar, Xodimlar, Filiallar, "Yana" (telefon menyusi) |
| `styles/global.css` | Dizayn tokenlari va komponent klasslari |

Qo'shimcha kutubxona faqat `react-router-dom` (sahifalar orasida yurish). Holat boshqaruvi uchun alohida kutubxona ishlatilmagan.

Ma'lum cheklovlar (texnik qarz):
* JWT `localStorage` da saqlanadi. Production'dan oldin httpOnly cookie'ga o'tkazishni ko'rib chiqish kerak.
* PWA hozircha faqat manifest bilan, offline ishlash (service worker) yo'q.
* Frontend uchun avtomatik testlar hali yo'q (qo'lda va Playwright skript bilan tekshirilgan).
