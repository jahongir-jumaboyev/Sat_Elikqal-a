# Rus tili lug‘at boti

Bot `vocabulary_units.json` faylidagi 12 ta bo‘limni `урок-1` dan `урок-12`
gacha tugmalar bilan ko‘rsatadi. Pastdagi **📚 Mavzular** tugmasi bo‘lim
tanlash menyusini ochadi. Bo‘limni tanlaganingizdan so‘ng faqat shu bo‘limdan
ruscha so‘z beradi; siz o‘zbekcha tarjimasini yozasiz. Bot javobni tekshiradi,
so‘z turkumi va JSON’dagi izohni ko‘rsatib, keyingi so‘zni beradi. **🎲
Tasodifiy so‘z** tugmasi yoki `/random` orqali barcha bo‘limlardan so‘z
olishingiz mumkin. `/start` bo‘lim tanlash menyusini qayta ochadi.

## Ishga tushirish (Windows PowerShell)

1. Python 3.10 yoki yangiroq versiyasini o‘rnating.
2. Shu papkada quyidagilarni bajaring:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Telegram’da `@BotFather` orqali bot ochib, token oling.
4. Tokenni muhit o‘zgaruvchisiga kiriting va botni ishga tushiring:

   ```powershell
   $env:BOT_TOKEN = "BOTFATHER_BERGAN_TOKEN"
   py main.py
   ```

`vocabulary_units.json` fayli `main.py` bilan bir papkada bo‘lishi kerak. Boshqa
joydagi JSON faylini ishlatish uchun `WORDS_FILE` muhit o‘zgaruvchisiga uning
yo‘lini kiriting. Flask web-serveri `0.0.0.0` manzilida ishlaydi; platforma
`PORT` muhit o‘zgaruvchisini bermasa, standart port `10000` ishlatiladi.
`/` manzili botning ishlayotganini bildiruvchi xabarni qaytaradi.
