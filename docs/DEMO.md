# Modiq taqdimot ssenariysi

Davomiyligi: 12–15 daqiqa. Maqsad: do'kon egasi, menejer va sotuvchining bir kunini boshidan oxirigacha ko'rsatish.

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

Demo do'kon "Moda Uz": Chilonzor do'koni, Yunusobod do'koni va Markaziy ombor. 10 ta tovar (futbolka, shim, ko'ylak, krossovka, tufli, sumka, kurtka, sviter), oxirgi 30 kunlik savdo.

Rasmlar demo ma'lumotda yo'q: taqdimot paytida 2–3 ta tovarga telefondan rasm yuklab ko'rsatish yaxshi taassurot qoldiradi.

## 1. Muammo (1 daqiqa)

Kichik kiyim do'koni egasi qaysi o'lchamdan nechta qolganini, qaysi tovar sotilmay yotganini va bugun qancha foyda qilganini bilmaydi. Hisob daftarda yoki Excelda yuritiladi, filiallar o'rtasida tovar yo'qoladi.

## 2. Egasi: hisobot (2 daqiqa)

Egasi bo'lib kiring → **Hisobot**.

- "Bugun" bloki: tushum, savdolar soni, o'rtacha chek.
- "Oxirgi 30 kun": tushum, **taxminiy yalpi foyda** (tushum − qaytarilgan pul − tannarx). Ijara va maosh hisobga olinmaganini ayting, shuning uchun "sof foyda" demaymiz.
- Kunlik tushum grafigi: ustun ustiga borilganda kun va summa chiqadi. Dam olish kunlari savdo ko'proq.
- **"Barcha filiallar"** tugmasi: ikki do'kon birgalikda.
- **Sotilmay turgan tovarlar**: "Qishki kurtka Arctic" va "Jun sviter" 30 kunda bitta ham sotilmagan, omborda ~35 mln so'mlik tovar turibdi. Shu yerda kelajakdagi **aqlli maslahatchi** haqida ayting: tizim bunday tovarlarni o'zi topib, qancha chegirma berishni tavsiya qiladi.
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
- Ikkita tovar qo'shing, biriga 10 000 so'm chegirma bering, to'lov turi "Karta" → **Savdoni yakunlash**. Chek chiqadi, uni chop etish mumkin.
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

## 7. Xodimlar va filiallar (1 daqiqa)

Egasi bo'lib: **Xodimlar** → **+ Yangi xodim**: telefon, parol, rol "Sotuvchi", filial tanlang. Mavjud xodimni tahrirlab, "qaytarish uchun mas'ul" belgisini ko'rsating.

**Filiallar** → **+ Yangi filial** → "Sergeli do'koni". Yuqoridagi filial tanlovida darhol paydo bo'ladi.

## 8. Telefon (30 soniya)

Brauzerni telefon o'lchamiga keltiring (F12 → telefon belgisi): pastki menyu, kassa telefon ekranida qulay. Kichik do'konda alohida kompyuter shart emas.

## 9. Keyingi qadamlar (1 daqiqa)

- Aqlli maslahatchi: sotilmay qolish xavfi bor tovarlar uchun aksiya va chegirma tavsiyasi.
- Inventarizatsiya (qoldiqni sanab tuzatish), chegirmalarni boshqarish.
- Internet yo'qligida ishlaydigan kassa.
- Serverga joylash (HTTPS, zaxira nusxa).

## Savollarga tayyor javoblar

- **Ma'lumot qayerda saqlanadi?** PostgreSQL bazasida. Har bir do'kon faqat o'z ma'lumotini ko'radi, bu testlar bilan tekshirilgan.
- **Ikki sotuvchi bir vaqtda oxirgi donani sotsa-chi?** Faqat bittasi sotadi, ikkinchisiga "qoldiq yetarli emas" chiqadi. Qoldiq hech qachon manfiy bo'lmaydi.
- **Tovar o'chirilsa, hisobotlar buziladimi?** Yo'q. Savdo tarixi bor tovar o'chirilmaydi, arxivlanadi.
- **Testlar bormi?** Backend'da 67 ta avtomatik test bor: savdo, qoldiq, ko'chirish, qaytarish, hisobot va huquqlar.
