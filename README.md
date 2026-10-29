# Aqlli Navbat — Telegram bot

Aiogram 3 asosida yaratilgan elektron navbat boti.

## Imkoniyatlar
- Foydalanuvchini ro‘yxatdan o‘tkazish
- Tashkilot va xizmatni tanlash
- Elektron navbat olish va holatini ko‘rish
- Faol navbatni bekor qilish
- Administrator statistikasi
- Navbatni chaqirish, yakunlash va bekor qilish
- Tashkilot va xizmatlarni buyruqlar bilan qo‘shish
- SQLite ma’lumotlar bazasi

## Windows’da ishga tushirish

1. Python 3.10 yoki yangiroq versiyani o‘rnating.
2. PowerShell’da loyiha papkasiga kiring.
3. Virtual muhit yaratish (ixtiyoriy, lekin tavsiya etiladi):

   ```powershell
   py -3.10 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Kutubxonalarni o‘rnating:

   ```powershell
   py -3.10 -m pip install -r requirements.txt
   ```

5. `.env.example` faylidan nusxa olib `.env` deb nomlang.
6. `.env` ichida:
   - `BOT_TOKEN` qiymatiga BotFather bergan tokenni yozing.
   - `ADMIN_IDS` qiymatiga Telegram raqamli user ID’ingizni yozing.
   - Tokenni hech kimga yubormang va GitHub’ga yuklamang.

7. Botni ishga tushiring:

   ```powershell
   py -3.10 bot.py
   ```

Birinchi ishga tushishda `navbat.db` bazasi va ikkita namunaviy tashkilot yaratiladi.

## Administrator buyruqlari
- `/admin` — boshqaruv paneli
- `/orgs` — tashkilotlar ro‘yxati va ID raqamlari
- `/addorg Tashkilot nomi` — tashkilot qo‘shish
- `/addservice 1 Xizmat nomi` — 1-ID tashkilotga xizmat qo‘shish

## Muhim
Hozirgi versiya botning o‘zida alohida SQLite bazadan foydalanadi. Vercel’dagi sayt bilan navbatlarni umumiy qilish uchun keyinchalik ikkalasini bitta doimiy backend/API va ma’lumotlar bazasiga ulash kerak bo‘ladi. Vercel serverless muhitida mahalliy SQLite fayli umumiy va doimiy baza sifatida mos emas.
