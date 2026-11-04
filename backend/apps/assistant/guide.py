"""Modiq'dan foydalanish qo'llanmasi: yordamchining yagona bilim manbai.

Tayyor mavzular (kartochkalar) shu matnlarni AI'siz, darhol ko'rsatadi. Erkin savolga AI ham faqat shu matnlarga
tayanib javob beradi. Dasturda tugma yoki sahifa o'zgarsa, shu fayl ham yangilanishi kerak: aks holda yordamchi
eskirgan yo'l-yo'riq beradi.

roles: "all" — hamma; "manager" — egasi va menejer; "owner" — faqat egasi;
"approver" — qaytarishni tasdiqlay oladiganlar (egasi, menejer yoki mas'ul sotuvchi).
"""

TOPICS = [
    # --- Hamma uchun ------------------------------------------------------------------------------
    {
        "id": "sale", "icon": "🧾", "roles": "all", "page": "/", "link": "Kassaga o'tish",
        "title": "Savdo qilish", "subtitle": "Kassada tovar sotish va chek",
        "body": """1. Chap menyudan «Kassa» bo'limini oching.
2. Qidiruv maydoniga SKU, shtrix-kod yoki tovar nomini yozing. Skaner bilan o'qitsangiz, bitta natija bo'lsa tovar o'zi savatga tushadi.
3. Natijalardan kerakli rang va o'lchamni bosing: tovar o'ngdagi «Savat»ga qo'shiladi.
4. Savatda «−» va «+» bilan sonini o'zgartiring. Qoldiqdan ko'p qo'shib bo'lmaydi.
5. To'lov turini tanlang: «Naqd», «Karta» yoki «Onlayn».
6. «Savdoni yakunlash» tugmasini bosing. Chek chiqadi: «Chop etish» yoki «Yangi savdo».

Aksiya bor tovarga chegirma o'zi qo'llanadi, eski narx ustidan chizilgan bo'lib ko'rinadi. Internet uzilib qayta bosilsa ham savdo ikki marta yozilmaydi.""",
    },
    {
        "id": "discount", "icon": "🏷", "roles": "all", "page": "/", "link": "Kassaga o'tish",
        "title": "Chegirma, aksiya va imtiyoz", "subtitle": "Qaysi chegirma qachon qo'llanadi",
        "body": """Kassada uch xil chegirma bor:
1. **Aksiya** — menejer yaratadi, muddat ichida kassada o'zi qo'llanadi. Sotuvchi hech narsa qilmaydi.
2. **Imtiyoz** — mijozning toifasi bo'yicha (masalan, VIP 10%). Savatda «Mijoz telefoni» maydoniga raqamni yozib «Topish»ni bosing — imtiyoz o'zi qo'llanadi.
3. **Qo'lda chegirma** — savatdagi tovar ostidagi «Qo'shimcha chegirma» maydoniga summani so'mda yozing.

Muhim qoidalar:
- Aksiya va imtiyoz qo'shilmaydi: mijoz uchun qaysi biri foydaliroq bo'lsa, o'shasi olinadi.
- Sotuvchi qo'lda ko'pi bilan sozlamadagi foizgacha (odatda 10%) chegirma bera oladi. Kattaroq chegirma kerak bo'lsa, menejer yoki do'kon egasini chaqiring.
- Avtomatik chegirma narxni tannarxdan pastga tushirmaydi.""",
    },
    {
        "id": "customer", "icon": "👤", "roles": "all", "page": "/customers", "link": "Mijozlarga o'tish",
        "title": "Mijoz qo'shish", "subtitle": "Kassada yoki «Mijozlar» bo'limida",
        "body": """Kassada (eng tez yo'l):
1. Savatdagi «Mijoz telefoni» maydoniga raqamni yozing (masalan, 90 123 45 67) va «Topish»ni bosing.
2. Mijoz topilmasa, «+ Yangi mijoz» tugmasi chiqadi. Ismini yozib «Saqlash»ni bosing — mijoz savdoga biriktiriladi.

«Mijozlar» bo'limida: «+ Yangi mijoz» → telefon, ism, izoh → «Saqlash».

Imtiyoz toifasini (VIP, Doimiy mijoz va h.k.) faqat egasi yoki menejer belgilaydi. Sotuvchi mijozning ismi va izohini o'zgartira oladi.""",
    },
    {
        "id": "bonus", "icon": "🎁", "roles": "all", "page": "/", "link": "Kassaga o'tish",
        "title": "Bonus bilan to'lash", "subtitle": "Keshbek qanday yig'iladi va ishlatiladi",
        "body": """1. Kassada savatga tovar qo'shing va mijozni telefon raqami bilan toping.
2. Mijozning bonusi «🎁 Bonus» qatorida ko'rinadi.
3. «Bonusdan to'lash» maydoniga summani yozing yoki «Maksimal» tugmasini bosing.
4. «Bonus bilan» qatori jami summadan ayiriladi. «Savdoni yakunlash»ni bosing.

Qoidalar:
- Har xariddan mijoz pul bilan to'lagan summaning foizi (odatda 3%) bonus bo'ladi. 1 ball = 1 so'm.
- Yangi bonus 24 soatdan keyin ishlatiladi.
- Chekning ko'pi bilan ma'lum qismi (odatda 35%) bonus bilan to'lanadi.
- Tovar qaytarilsa, bonus bilan to'langan qism mijoz balansiga qaytadi.

Mijozning bonus tarixi: «Mijozlar» bo'limida mijoz qatoridagi 🎁 tugmasi.""",
    },
    {
        "id": "return", "icon": "↩", "roles": "all", "page": "/sales", "link": "Savdolarga o'tish",
        "title": "Yaroqsiz tovarni qaytarish", "subtitle": "Faqat yaroqsiz tovar, 24 soat ichida",
        "body": """1. «Savdolar» bo'limini oching va kerakli chekni bosing.
2. «↩ Yaroqsiz tovarni qaytarish» tugmasini bosing.
3. Qaytariladigan tovar sonini belgilang va «Yaroqsizlik sababi»ni yozing (masalan, choki so'kilgan).
4. «Qaytarish» tugmasini bosing.

- Faqat yaroqsiz tovar qaytariladi, muddat — sotuvdan keyin 24 soat.
- Agar sizda tasdiqlash huquqi bo'lmasa, so'rov «Tasdiq kutilmoqda» holatiga tushadi. Mas'ul xodim tasdiqlagach, mijozga pulni qaytarasiz.
- Qaytarilgan tovar sotuvga qaytmaydi, hisobdan chiqariladi.""",
    },
    {
        "id": "stock", "icon": "📦", "roles": "all", "page": "/stock", "link": "Qoldiqqa o'tish",
        "title": "Qoldiqni ko'rish", "subtitle": "Qaysi o'lchamdan nechta qolgan",
        "body": """1. «Qoldiq» bo'limini oching.
2. Qidiruvga SKU yoki tovar nomini yozing.
3. Faqat tugayotganlarni ko'rish uchun «▲ Faqat kam qolganlar» tugmasini bosing.

Holatlar: «● Yetarli», «▲ Kam qolgan» (minimal qoldiqdan kam), «✕ Tugagan». Qoldiq har bir rang va o'lcham (variant) uchun alohida ko'rsatiladi. Ro'yxat yuqorida tanlangan filial bo'yicha.""",
    },
    {
        "id": "sales", "icon": "📈", "roles": "all", "page": "/sales", "link": "Savdolarga o'tish",
        "title": "Savdolar tarixi va chek", "subtitle": "Eski chekni topish va chop etish",
        "body": """1. «Savdolar» bo'limini oching — tanlangan filialdagi savdolar ro'yxati.
2. Kerakli savdoni bosing — chek ochiladi.
3. «Chop etish» tugmasi bilan chekni qayta chop eting.

Chekda aksiya, imtiyoz, bonus va mijoz ko'rinadi. Sotuvchi tannarx va foydani ko'rmaydi.""",
    },
    {
        "id": "branch", "icon": "🏬", "roles": "all", "page": None, "link": None,
        "title": "Filialni tanlash", "subtitle": "Boshqa do'kon yoki omborga o'tish",
        "body": """Yuqori chap burchakda do'kon nomi yonidagi ro'yxatdan filialni tanlang. Kassa, qoldiq, savdolar, kirim va ko'chirish tanlangan filial bo'yicha ishlaydi.

Ro'yxat ko'rinmasa, sizga bitta filial biriktirilgan. Boshqa filialga ruxsat kerak bo'lsa, do'kon egasiga murojaat qiling.""",
    },
    # --- Qaytarishni tasdiqlovchilar --------------------------------------------------------------
    {
        "id": "return_approve", "icon": "✅", "roles": "approver", "page": "/returns", "link": "Qaytarishga o'tish",
        "title": "Qaytarishni tasdiqlash", "subtitle": "Kutilayotgan so'rovlar",
        "body": """1. «Qaytarish» bo'limini oching. «Tasdiq kutilmoqda» holatidagi so'rovlar ko'rinadi.
2. So'rovdagi sababni o'qing va «Tasdiqlash» yoki «Rad etish»ni bosing.
3. Tasdiqlansa, xabarda mijozga qancha pul qaytarish kerakligi yoziladi. Bonus bilan to'langan qism mijoz balansiga o'zi qaytadi.""",
    },
    # --- Egasi va menejer -------------------------------------------------------------------------
    {
        "id": "product_new", "icon": "👕", "roles": "manager", "page": "/products/new", "link": "Yangi tovar",
        "title": "Yangi tovar qo'shish", "subtitle": "Rang × o'lcham variantlari bilan",
        "body": """1. «Tovarlar» bo'limida «+ Yangi tovar» tugmasini bosing.
2. «Tovar nomi», «Artikul», «Xarid narxi», «Sotuv narxi»ni yozing. Kerak bo'lsa «Kategoriya», «Brend», «Mavsum», «Rasm».
3. «Ranglar» va «O'lchamlar»dan keraklilarini bosib tanlang. Ro'yxatda yo'q bo'lsa, yoniga yozib «Qo'shish»ni bosing.
4. «Saqlash»ni bosing. Har bir rang × o'lcham alohida variant (SKU) bo'ladi.

Tovar qo'shilganda qoldig'i 0 bo'ladi. Qoldiq «Kirim» orqali kiritiladi.""",
    },
    {
        "id": "product_edit", "icon": "✎", "roles": "manager", "page": "/products", "link": "Tovarlarga o'tish",
        "title": "Tovarni tahrirlash", "subtitle": "Narx, rasm, shtrix-kod, yangi variant",
        "body": """1. «Tovarlar» bo'limida tovar qatoridagi «✎ Tahrirlash»ni bosing.
2. «Asosiy ma'lumotlar»: nom, narxlar, mavsum va boshqalar → «Saqlash».
3. «Rasm»: telefon yoki kompyuterdan rasm yuklang.
4. «Variantlar»: har bir variantga «Shtrix-kod» yoki «Alohida narx» yozing va qatordagi «Saqlash»ni bosing.
5. «Yangi variantlar qo'shish»: rang va o'lcham tanlab, kombinatsiyalarni qo'shish tugmasini bosing.

Savdo tarixi bor tovar o'chirilmaydi, arxivlanadi.""",
    },
    {
        "id": "receipt", "icon": "📥", "roles": "manager", "page": "/receipts", "link": "Kirimga o'tish",
        "title": "Kirim (tovar qabul qilish)", "subtitle": "Yetkazib beruvchidan kelgan tovar",
        "body": """1. Yuqoridan tovar qabul qilinadigan filialni (odatda omborni) tanlang.
2. «Kirim» bo'limida «+ Yangi kirim» tugmasini bosing.
3. «Yetkazib beruvchi», «Hujjat raqami», «Sana»ni yozing.
4. «Tovar qo'shish» maydonida SKU yoki nom bilan variantlarni toping, soni va xarid narxini yozing.
5. «Saqlash va tasdiqlash» — qoldiq darhol oshadi. Yoki «Qoralama saqlash», keyin ro'yxatdan «Tasdiqlash».

Qoldiq faqat tasdiqlanganda oshadi. Ikki marta bosish qoldiqni ikki marta oshirmaydi.""",
    },
    {
        "id": "transfer", "icon": "🔁", "roles": "manager", "page": "/transfers", "link": "Ko'chirishga o'tish",
        "title": "Filiallar orasida ko'chirish", "subtitle": "Ombordan do'konga tovar jo'natish",
        "body": """1. Yuqoridan tovar jo'natiladigan filialni tanlang.
2. «Ko'chirish» bo'limida «+ Yangi ko'chirish» tugmasini bosing.
3. «Qayerga» filialni tanlang, «Tovar qo'shish» orqali variant va sonini kiriting.
4. «Saqlash va jo'natish»ni bosing — jo'natuvchi filial qoldig'i darhol kamayadi, tovar «Yo'lda» bo'ladi.
5. Qabul qiluvchi filialni tanlab, «Ko'chirish» bo'limida «Qabul qilish»ni bosing — qoldiq o'sha yerda oshadi.

Jo'natilgan ko'chirishni bekor qilsangiz, tovar jo'natuvchiga qaytadi.""",
    },
    {
        "id": "promotion", "icon": "🏷", "roles": "manager", "page": "/promotions", "link": "Aksiyalarga o'tish",
        "title": "Aksiya yaratish", "subtitle": "Mavsum, kategoriya yoki tanlangan tovarlarga",
        "body": """1. «Aksiyalar» bo'limida «+ Yangi aksiya» tugmasini bosing.
2. «Nomi»ni yozing va «Qamrov»ni tanlang: «Barcha tovarlar», «Mavsum bo'yicha», «Kategoriya bo'yicha» yoki «Tanlangan tovarlar».
3. «Chegirma turi»: foiz yoki har bir dona uchun summa. Qiymatini yozing.
4. «Boshlanish sanasi» va «Tugash sanasi»ni belgilang (tugash kuni ham kiradi). Mavsumni tanlasangiz, tugash sanasi mavsum oxiriga o'zi qo'yiladi.
5. «Saqlash». Muddat ichida kassada o'zi qo'llanadi.

Ro'yxatda natija ko'rinadi: aksiyadan oldin va aksiya davomida sotilgan dona. «To'xtatish» aksiyani muddatidan oldin to'xtatadi.""",
    },
    {
        "id": "insights", "icon": "💡", "roles": "manager", "page": "/insights", "link": "Tavsiyalarga o'tish",
        "title": "Tavsiyalar", "subtitle": "Sotilmay qolayotgan tovarga qancha chegirma",
        "body": """1. «Tavsiyalar» bo'limini oching. Har bir tovarda xavf darajasi (🔴 yuqori, 🟠 o'rta, 🟡 past) va tavsiya qilingan chegirma bor.
2. «Nega?» qismida sababi yozilgan: necha kun sotilmagan, qoldiq necha kunga yetadi, mavsum tugayaptimi.
3. «🏷 Aksiya yaratish» tugmasi aksiya formasini tayyor ochadi — muddatni tekshirib «Saqlash»ni bosing.
4. Kerak bo'lmasa «Rad etish (30 kun)».

«✨ AI xulosasi» ro'yxatni qisqa tushuntirib beradi. «⚙ Qoidalar»da kunlar va foizlarni o'zgartirish mumkin.""",
    },
    {
        "id": "dashboard", "icon": "📊", "roles": "manager", "page": "/dashboard", "link": "Hisobotga o'tish",
        "title": "Hisobot", "subtitle": "Tushum, foyda, eng ko'p sotilganlar",
        "body": """«Hisobot» bo'limida:
- «Bugun»: tushum, savdolar soni, o'rtacha chek.
- «Oxirgi N kun» (7, 30 yoki 90 kunni tanlang): tushum, taxminiy yalpi foyda, qaytarilgan pul, yaroqsiz tovar.
- «Kunlik tushum» grafigi, «Eng ko'p sotilganlar», «To'lov turlari», «Sotilmay turgan tovarlar».

Taxminiy yalpi foyda = tushum − qaytarilgan pul − tannarx. Ijara va maosh hisobga olinmagan, bu sof foyda emas.""",
    },
    {
        "id": "pricing_settings", "icon": "⚙", "roles": "manager", "page": "/promotions", "link": "Aksiyalarga o'tish",
        "title": "Chegirma va bonus sozlamalari", "subtitle": "Sotuvchi chegarasi, bonus foizi",
        "body": """«Aksiyalar» bo'limining pastida «Chegirma va bonus sozlamalari»:
- Sotuvchi qo'lda beradigan chegirma chegarasi, % (0 — sotuvchi qo'lda chegirma bera olmaydi).
- Bonus tizimini yoqish yoki o'chirish.
- Har xariddan bonus foizi.
- Bonus bilan to'lash chegarasi (chekning foizi).

O'zgartirib «Saqlash»ni bosing.""",
    },
    {
        "id": "customer_groups", "icon": "★", "roles": "manager", "page": "/customers", "link": "Mijozlarga o'tish",
        "title": "Imtiyoz toifalari", "subtitle": "VIP, Doimiy mijoz, Xodim",
        "body": """1. «Mijozlar» bo'limining pastida «Imtiyoz toifalari».
2. «Toifa nomi» va «Chegirma, %» (0–50) yozib «+ Qo'shish».
3. Mijozga toifa berish: mijoz qatoridagi «✎» → «Imtiyoz toifasi» → «Saqlash».

Imtiyoz aksiya bilan qo'shilmaydi: kassada foydalirog'i olinadi.""",
    },
    {
        "id": "branches", "icon": "🏬", "roles": "manager", "page": "/branches", "link": "Filiallarga o'tish",
        "title": "Filial qo'shish", "subtitle": "Do'kon yoki ombor",
        "body": """1. «Filiallar» bo'limida «+ Yangi filial».
2. «Nomi», «Turi» (do'kon yoki ombor), «Manzil» → «Saqlash».

Filial o'chirilmaydi: «✎ Tahrirlash»da «Faol» belgisini olib tashlab yopiladi, tarixi saqlanadi.""",
    },
    {
        "id": "staff", "icon": "👥", "roles": "owner", "page": "/staff", "link": "Xodimlarga o'tish",
        "title": "Xodim qo'shish va huquqlar", "subtitle": "Sotuvchi, menejer, filiallar",
        "body": """1. «Xodimlar» bo'limida «+ Yangi xodim».
2. «Telefon», «F.I.Sh.», «Parol», «Rol» (sotuvchi yoki menejer) ni kiriting.
3. Sotuvchi uchun «Filiallar»ni belgilang — u faqat shu filiallarda ishlaydi.
4. Kerak bo'lsa «Yaroqsiz tovar qaytarilishini tasdiqlay oladi (mas'ul shaxs)» belgisini qo'ying.
5. «Saqlash».

Xodim qo'shish va rolini o'zgartirish faqat do'kon egasiga mumkin. Menejer ro'yxatni ko'radi.""",
    },
]

# Joriy sahifa (frontend yo'li) -> AI'ga tushunarli nom.
PAGES = {
    "/": "Kassa", "/dashboard": "Hisobot", "/insights": "Tavsiyalar", "/products": "Tovarlar",
    "/products/new": "Yangi tovar", "/receipts": "Kirim", "/transfers": "Ko'chirish", "/stock": "Qoldiq",
    "/sales": "Savdolar", "/returns": "Qaytarish", "/customers": "Mijozlar", "/promotions": "Aksiyalar",
    "/staff": "Xodimlar", "/branches": "Filiallar", "/more": "Bo'limlar",
}


def page_name(path: str) -> str:
    if path.startswith("/products/") and path.endswith("/edit"):
        return "Tovarni tahrirlash"
    return PAGES.get(path or "", "")


def allowed(topic: dict, membership) -> bool:
    roles = topic["roles"]
    if roles == "all":
        return True
    if roles == "manager":
        return membership.is_manager
    if roles == "owner":
        return membership.role == membership.Role.OWNER
    if roles == "approver":
        return membership.may_approve_returns
    return False


def topics_for(membership) -> list[dict]:
    return [t for t in TOPICS if allowed(t, membership)]
