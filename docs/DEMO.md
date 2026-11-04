# Modiq taqdimot ssenariysi

Davomiyligi: 15–18 daqiqa. Maqsad: do'kon egasi, menejer va sotuvchining bir kunini boshidan oxirigacha ko'rsatish.

## Tayyorgarlik (taqdimotdan oldin)

```bash
cd backend
python manage.py migrate
python manage.py seed_demo --reset     # har safar toza demo do'kon
python manage.py runserver
```

Ikkinchi terminalda:

```bash
cd frontend
npm run dev
```

Brauzerda http://localhost:5173 ni oching. Sotuvchi ko'rinishini ko'rsatish uchun ikkinchi brauzer oynasini (yoki maxfiy oynani) ham tayyorlab qo'ying.

| Kim | Telefon | Parol | Nimani ko'radi |
|---|---|---|---|
| Jasur Karimov, do'kon egasi | 90 000 00 01 | Demo-12345 | Hammasi, xodimlarni boshqaradi |
| Dilnoza Rahimova, menejer | 90 000 00 02 | Demo-12345 | Hammasi, xodimlardan tashqari |
| Aziz Tursunov, sotuvchi | 90 000 00 03 | Demo-12345 | Faqat Chilonzor do'koni, tannarxni ko'rmaydi |
| Malika Yusupova, sotuvchi | 90 000 00 04 | Demo-12345 | Faqat Yunusobod do'koni, qaytarishni tasdiqlay oladi |

Demo do'kon "Moda Uz": Chilonzor do'koni, Yunusobod do'koni va Markaziy ombor. 10 ta tovar (futbolka, shim, ko'ylak, krossovka, tufli, sumka, kurtka, sviter), oxirgi 30 kunlik savdo. Kurtka va sviter 69 kun oldin kelgan va bitta ham sotilmagan.

Mijozlar (kassada telefon bilan topiladi):

| Mijoz | Telefon | Imtiyoz |
|---|---|---|
| Nodira Aliyeva | 90 123 45 01 | VIP 10% |
| Bekzod Qodirov | 90 123 45 02 | Doimiy mijoz 5% |
| Gulnora Saidova | 90 123 45 04 | Oddiy (imtiyozsiz) |
| Zarina Hamidova | 90 123 45 06 | Xodim 15% |

Har bir mijozda o'tgan xaridlardan yig'ilgan bonus bor. Aksiyalar: "Futbolka haftaligi" (−10%, faol) va "Yangi yil" (−15%, boshlanmagan).

Rasmlar demo ma'lumotda yo'q: taqdimot paytida 2–3 ta tovarga telefondan rasm yuklab ko'rsatish yaxshi taassurot qoldiradi.

## 1. Muammo (1 daqiqa)

Kichik kiyim do'koni egasi qaysi o'lchamdan nechta qolganini, qaysi tovar sotilmay yotganini va bugun qancha foyda qilganini bilmaydi. Hisob daftarda yoki Excelda yuritiladi, filiallar o'rtasida tovar yo'qoladi.

## 2. Egasi: hisobot (2 daqiqa)

Egasi bo'lib kiring → **Hisobot**.

- "Bugun" bloki: tushum, savdolar soni, o'rtacha chek.
- "Oxirgi 30 kun": tushum, **taxminiy yalpi foyda** (tushum − qaytarilgan pul − tannarx). Ijara va maosh hisobga olinmaganini ayting, shuning uchun "sof foyda" demaymiz.
- Kunlik tushum grafigi: ustun ustiga borilganda kun va summa chiqadi. Dam olish kunlari savdo ko'proq.
- **"Barcha filiallar"** tugmasi: ikki do'kon birgalikda.
- **Sotilmay turgan tovarlar**: "Qishki kurtka Arctic" va "Jun sviter" 30 kunda bitta ham sotilmagan, omborda ~35 mln so'mlik tovar turibdi. **💡 Tavsiyalar** tugmasi bilan 7-bandga o'tamiz.
- Yuqoridagi sariq xabar: "1 ta qaytarish so'rovi tasdiqni kutmoqda". Bunga 6-bandda qaytamiz.

## 3. Tovar: rang × o'lcham (2 daqiqa)

**Tovarlar** → "Futbolka Basic" qatorini oching: 3 rang × 4 o'lcham = 12 ta variant, har birining o'z SKU va qoldig'i bor.

**✎ Tahrirlash**:
- Rasm yuklang (telefon rasmi avtomatik siqiladi).
- Bitta variantga shtrix-kod yozing, masalan `4780001234567`. Keyin kassada shu kod bilan qidiramiz.
- "Yangi variantlar qo'shish": Ko'k rang + S, M → "2 ta kombinatsiyani qo'shish".

Ixtiyoriy: **+ Yangi tovar** orqali 30 soniyada yangi tovar yarating (ranglar va o'lchamlarni chip bilan tanlash).

## 4. Ombor: kirim va ko'chirish (2 daqiqa)

Yuqoridan filialni **Markaziy ombor** ga almashtiring.

- **Kirim**: "Urban Style" dan kelgan qoralama kirim turibdi → **Tasdiqlash**. Qoldiq faqat tasdiqlanganda oshadi, ikki marta bosish qoldiqni ikki marta oshirmaydi.
- **Ko'chirish**: "Yo'lda" holatidagi ko'chirish bor (Ombor → Yunusobod). Qatorni ochib, tovarlarni ko'rsating.
- **+ Yangi ko'chirish**: ombordan Chilonzorga 5 ta futbolka → "Saqlash va jo'natish". Ombor qoldig'i darhol kamayadi.

Filialni **Yunusobod do'koni** ga almashtiring → **Ko'chirish** → yo'ldagi ko'chirishni **Qabul qilish**. **Qoldiq** sahifasida tovar paydo bo'ladi.

## 5. Sotuvchi: kassa (3 daqiqa)

Ikkinchi oynada **Aziz (sotuvchi)** bo'lib kiring.

- Menyuda Kirim, Hisobot, Xodimlar yo'q. Sotuvchi faqat o'z do'konini ko'radi.
- **Kassa**: "futbolka" deb qidiring yoki 3-banddagi shtrix-kodni kiriting (skaner Enter yuboradi va tovar darhol savatga tushadi).
- "Futbolka Basic" qo'shing: "Futbolka haftaligi" aksiyasi (−10%) o'zi qo'llanadi, eski narx ustidan chizilgan holda ko'rinadi.
- Ikkinchi tovarga 5 000 so'm chegirma bering. Keyin 50 000 yozib ko'ring: "sotuvchi ko'pi bilan 10% chegirma bera oladi" xatosi chiqadi. Sotuvchi o'zboshimchalik bilan katta chegirma bera olmaydi.
- **Mijoz telefoni**ga `90 123 45 01` → **Topish**: Nodira Aliyeva, VIP 10%. Aksiya bor tovarda 10% aksiya qoladi (ustma-ust qo'shilmaydi), aksiyasiz tovarga 10% imtiyoz qo'llanadi.
- 🎁 Bonus balansi ko'rinadi → **Maksimal** → chekning ko'pi bilan 35 foizi bonus bilan to'lanadi. Pastda "Bu xariddan bonus: +..." (pul bilan to'langan summaning 3%).
- To'lov turi "Karta" → **Savdoni yakunlash**. Chekda aksiya, imtiyoz, bonus va mijoz ko'rinadi, uni chop etish mumkin.
- Qoldiqdan ko'p sotishga urinib ko'ring: "+" tugmasi o'chadi. Server ham ruxsat bermaydi.
- **Savdolar**: sotuvchi tannarx va foydani ko'rmaydi (egasi ko'radi).

Internet uzilib qolsa ham savdo ikki marta yozilmasligini ayting: har bir savdoning o'z kaliti bor.

## 6. Qaytarish: faqat yaroqsiz tovar (2 daqiqa)

Aziz bo'lib: **Savdolar** → hozirgi savdoni oching → **↩ Yaroqsiz tovarni qaytarish** → 1 dona, sabab "Choki so'kilgan" → **Qaytarish**.

- Aziz qaytarishni tasdiqlay olmaydi, shuning uchun so'rov "Tasdiq kutilmoqda" holatiga tushadi.

Egasi oynasiga qayting → **Qaytarish** → ikkita kutilayotgan so'rov → **Tasdiqlash**. Xabar: "Mijozga ... so'm qaytaring".

Tushuntiring:
- faqat yaroqsiz tovar qaytariladi, muddat sotuvdan keyin 24 soat;
- qaytarilgan tovar sotuvga qaytmaydi, hisobdan chiqariladi va hisobotda "Yaroqsiz tovar" bo'lib ko'rinadi;
- egasi istalgan sotuvchiga "qaytarish uchun mas'ul" huquqini bera oladi (Malika shunday sotuvchi).

## 7. Chegirma, mavsum va tavsiyalar (3 daqiqa)

Egasi bo'lib: **💡 Tavsiyalar**.

- Yuqorida: xavf ostidagi tovarlar soni va omborda muzlab turgan pul.
- "Qishki kurtka Arctic": 🔴 yuqori xavf, **−30%**. **Nega?** bo'limi: 69 kun sotilmagan, omborda qancha pul turibdi, 30% chegirmada ham narx tannarxdan qancha yuqori qoladi.
- "Krossovka Run": 🟠 **mavsum** qoidasi: "Bahor-Yoz" mavsumi tugagan, keyingi mavsum martda.
- Futbolkalarda "Faol aksiya bor" yozuvi: tizim bir tovarga ikkinchi aksiya taklif qilmaydi.
- **✨ AI xulosasi** → **Xulosa olish**: Gemini ro'yxatni o'qib, egaga qisqa maslahat yozadi. Muhim: qaysi tovar va necha foiz ekanini **qoidalar** hisoblaydi, AI faqat tushuntiradi. Internet yoki kalit bo'lmasa ham tavsiyalar ishlaydi.
- Kurtkada **🏷 Aksiya yaratish** → forma tovar va 30% bilan to'lib ochiladi → **Saqlash**.

Kassaga qayting, kurtkani savatga qo'shing: 30% aksiya qo'llanadi. **🏷 Aksiyalar** sahifasida "💡 Tavsiyadan" belgisi va natija ustuni (aksiyadan oldin va aksiya davomida sotilgan dona) ko'rinadi.

Mavsumiy aksiya: **+ Yangi aksiya** → Qamrov "Mavsum bo'yicha" → "Kuz-Qish": tugash sanasi o'zi mavsum oxiriga (fevral) qo'yiladi.

**⚙ Qoidalar** (Tavsiyalar sahifasida): chegaralar va foizlarni egasi o'zgartira oladi. **Aksiyalar** sahifasi pastida: sotuvchining qo'lda chegirma chegarasi, bonus foizi va bonus bilan to'lash chegarasi.

**👤 Mijozlar**: xaridlar soni va summasi, bonus balansi (🎁 tugmasi tarixini ochadi), imtiyoz toifalarini boshqarish.

## 8. Xodimlar va filiallar (1 daqiqa)

Egasi bo'lib: **Xodimlar** → **+ Yangi xodim**: telefon, parol, rol "Sotuvchi", filial tanlang. Mavjud xodimni tahrirlab, "qaytarish uchun mas'ul" belgisini ko'rsating.

**Filiallar** → **+ Yangi filial** → "Sergeli do'koni". Yuqoridagi filial tanlovida darhol paydo bo'ladi.

## 9. Telefon (30 soniya)

Brauzerni telefon o'lchamiga keltiring (F12 → telefon belgisi): pastki menyu, kassa telefon ekranida qulay. Kichik do'konda alohida kompyuter shart emas.

## 10. Keyingi qadamlar (1 daqiqa)

- Inventarizatsiya (qoldiqni sanab tuzatish).
- Mijozga SMS/Telegram orqali bonus va aksiya xabarlari.
- Internet yo'qligida ishlaydigan kassa.
- Serverga joylash (HTTPS, zaxira nusxa).

## Savollarga tayyor javoblar

- **Ma'lumot qayerda saqlanadi?** PostgreSQL bazasida. Har bir do'kon faqat o'z ma'lumotini ko'radi, bu testlar bilan tekshirilgan.
- **Ikki sotuvchi bir vaqtda oxirgi donani sotsa-chi?** Faqat bittasi sotadi, ikkinchisiga "qoldiq yetarli emas" chiqadi. Qoldiq hech qachon manfiy bo'lmaydi.
- **Tovar o'chirilsa, hisobotlar buziladimi?** Yo'q. Savdo tarixi bor tovar o'chirilmaydi, arxivlanadi.
- **Testlar bormi?** Backend'da 120 ta avtomatik test bor: savdo, qoldiq, ko'chirish, qaytarish, hisobot, huquqlar, aksiya, imtiyoz, bonus va tavsiyalar.
- **Aksiya, imtiyoz va bonus birga qo'llansa, do'kon zarar ko'rmaydimi?** Aksiya va imtiyoz ustma-ust qo'shilmaydi, ikkisidan mijoz uchun foydalirog'i olinadi. Avtomatik chegirma ham, bonus ham narxni tannarxdan pastga tushirmaydi. Bonus chekning ko'pi bilan 35 foizini qoplaydi.
- **Sotilmay qolishi mumkin bo'lgan tovarga qanday chegirma qo'llaysiz?** Tizim har bir tovar uchun oxirgi sotuvdan beri kunlarni, qoldiq hozirgi tezlikda necha kunga yetishini va mavsum tugashini hisoblaydi. Shundan xavf darajasi va chegirma (30/20/10%) chiqadi, sababi bilan. Menejer bir bosishda aksiya yaratadi, keyin natijasini (aksiyadan oldin va keyin sotilgan dona) ko'radi.
- **AI noto'g'ri tavsiya bersa-chi?** AI tavsiya bermaydi, faqat qoidalar chiqargan ro'yxatni tushuntiradi. Foizni va tovarni qoidalar hisoblaydi, har birining sababi ko'rsatiladi.
- **Bonus berilgandan keyin tovar qaytarilsa-chi?** Bonus 24 soatdan keyin ishlatiladi, bu qaytarish muddati bilan bir xil. Qaytarishda yig'ilgan bonus bekor qilinadi, bonus bilan to'langan qism esa mijoz balansiga qaytadi.
