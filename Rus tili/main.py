import json
import logging
import os
import random
import re
import threading
from pathlib import Path
from typing import Any

from flask import Flask
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


LOGGER = logging.getLogger(__name__)
app = Flask(__name__)
RANDOM_WORD_BUTTON = "🎲 Tasodifiy so‘z"
TOPICS_BUTTON = "📚 Mavzular"
KEYBOARD = ReplyKeyboardMarkup(
    [[RANDOM_WORD_BUTTON], [TOPICS_BUTTON]],
    resize_keyboard=True,
)
Word = dict[str, str | int]


@app.route("/")
def home() -> str:
    return "Bot ishlayapti!"


def run_web() -> None:
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


def load_words(file_path: Path) -> tuple[list[Word], dict[int, dict[str, Any]]]:
    try:
        with file_path.open(encoding="utf-8") as dictionary_file:
            data: Any = json.load(dictionary_file)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Lug‘at JSON fayli topilmadi: {file_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Lug‘at faylida JSON xatosi ({error.lineno}-qator): {error.msg}"
        ) from error

    if not isinstance(data, dict) or not isinstance(data.get("units"), list):
        raise ValueError("JSON faylida 'units' ro‘yxati bo‘lishi kerak.")

    words: list[Word] = []
    units: dict[int, dict[str, Any]] = {}
    for unit in data["units"]:
        if not isinstance(unit, dict):
            continue
        unit_number = unit.get("unit")
        title = unit.get("title", "Lug‘at")
        unit_words = unit.get("words", [])
        if (
            not isinstance(unit_number, int)
            or isinstance(unit_number, bool)
            or not isinstance(title, str)
            or not isinstance(unit_words, list)
        ):
            continue

        loaded_unit_words: list[Word] = []
        for word in unit_words:
            if (
                isinstance(word, dict)
                and isinstance(word.get("ru"), str)
                and isinstance(word.get("uz"), str)
                and word["ru"].strip()
                and word["uz"].strip()
            ):
                loaded_word: Word = {
                    "ru": word["ru"].strip(),
                    "uz": word["uz"].strip(),
                    "lesson": title.strip() or "Lug‘at",
                    "unit": unit_number,
                    "pos": word.get("pos", ""),
                    "description": word.get("description", ""),
                }
                loaded_unit_words.append(loaded_word)
                words.append(loaded_word)

        if loaded_unit_words:
            units[unit_number] = {
                "title": title.strip() or "Lug‘at",
                "words": loaded_unit_words,
            }

    if not words:
        raise ValueError("JSON faylida 'units' ichidan lug‘at so‘zlari topilmadi.")
    return words, units


def unit_keyboard(units: dict[int, dict[str, Any]]) -> InlineKeyboardMarkup:
    unit_numbers = sorted(units)
    rows = [
        [
            InlineKeyboardButton(f"урок-{number}", callback_data=f"unit:{number}")
            for number in unit_numbers[index : index + 3]
        ]
        for index in range(0, len(unit_numbers), 3)
    ]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        context.user_data.pop("selected_unit", None)
        context.user_data.pop("current_word", None)
        context.user_data.pop("unit_score", None)
        await update.message.reply_text(
            "Salom! O‘rganish uchun урок-1 dan урок-12 gacha bo‘lgan bo‘limlardan "
            "birini tanlang. Men ruscha so‘zni beraman, siz o‘zbekchasini yozasiz.\n"
            "Pastdagi 📚 Mavzular tugmasini bosib урокni tanlang yoki 🎲 tugmasi "
            "orqali tasodifiy so‘z oling.",
            reply_markup=KEYBOARD,
        )
        await send_topics(update, context)


async def send_topics(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    if not message:
        return
    context.user_data.pop("current_word", None)
    await message.reply_text(
        "Mavzuni tanlang:",
        reply_markup=unit_keyboard(context.application.bot_data["units"]),
    )


async def topics_button(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data.pop("selected_unit", None)
    await send_topics(update, context)


async def select_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    unit_number = int(query.data.split(":", maxsplit=1)[1])
    units: dict[int, dict[str, Any]] = context.application.bot_data["units"]
    message = update.effective_message
    if not message:
        return
    if unit_number not in units:
        await message.reply_text("Bu урок lug‘atda topilmadi.")
        return
    context.user_data.pop("unit_score", None)
    context.user_data["selected_unit"] = unit_number
    context.user_data.setdefault("unit_score", {}).setdefault(
        f"unit:{unit_number}", {"correct": 0, "total": 0, "seen": set()}
    )
    await message.reply_text(
        f"📚 урок-{unit_number}: {units[unit_number]['title']}"
    )
    await send_random_word(update, context)


async def send_random_word(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    if not message:
        return

    words: list[Word] = context.application.bot_data["words"]
    selected_unit = context.user_data.get("selected_unit")
    if selected_unit is not None:
        unit_words = context.application.bot_data["units"].get(selected_unit, {}).get(
            "words", []
        )
        if unit_words:
            progress = unit_progress(context)
            if progress is None:
                progress = {"correct": 0, "total": 0, "seen": set()}
                context.user_data.setdefault("unit_score", {}).setdefault(
                    f"unit:{selected_unit}", progress
                )
            remaining_words = [
                word for word in unit_words if get_word_key(word) not in progress["seen"]
            ]
            if not remaining_words:
                await finish_unit(update, context)
                return
            words = remaining_words
    word = random.choice(words)
    context.user_data["current_word"] = word
    await message.reply_text(
        f"📚 урок-{word['unit']}: {word['lesson']}\n"
        f"🇷🇺 {word['ru']}\n"
        "🇺🇿 O‘zbekcha tarjimasini yozing:",
        reply_markup=KEYBOARD,
    )


async def send_global_random_word(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data.pop("selected_unit", None)
    await send_random_word(update, context)


def normalize_answer(answer: str) -> str:
    apostrophe_variants = "ʻʼ‘’＇`´՚"
    return "".join(
        character
        for character in answer.casefold()
        if character.isalnum() and character not in apostrophe_variants
    )


def accepted_answers(translation: str) -> set[str]:
    answers = set()
    for alternative in translation.split("/"):
        full_translation = normalize_answer(alternative)
        if full_translation:
            answers.add(full_translation)
        base_translation = re.sub(r"\s*\([^)]*\)", "", alternative).strip()
        normalized = normalize_answer(base_translation)
        if normalized:
            answers.add(normalized)
    return answers


def get_word_key(word: Word) -> str:
    return str(
        word.get("id")
        or f"{word.get('unit', '')}:{word.get('lesson', '')}:{word.get('ru', '')}:{word.get('uz', '')}"
    )


def get_score_summary(score: dict[str, int]) -> str:
    correct = int(score.get("correct", 0))
    total = int(score.get("total", 0))
    return f"📊 Hisob: {correct}/{total}"


def record_answer(score: dict[str, int] | None, is_correct: bool) -> dict[str, int]:
    if score is None:
        score = {}
    score["total"] = int(score.get("total", 0)) + 1
    if is_correct:
        score["correct"] = int(score.get("correct", 0)) + 1
    return score


def unit_progress(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any] | None:
    selected_unit = context.user_data.get("selected_unit")
    if selected_unit is None:
        return None
    unit_key = f"unit:{selected_unit}"
    progress = context.user_data.setdefault("unit_score", {}).setdefault(
        unit_key,
        {"correct": 0, "total": 0, "seen": set()},
    )
    return progress


async def finish_unit(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    if not message:
        return
    selected_unit = context.user_data.get("selected_unit")
    progress = unit_progress(context)
    if selected_unit is None or progress is None:
        await message.reply_text("Mavzu yakuni bo‘yicha natija aniqlanmagan.")
        return
    await message.reply_text(
        f"🎉 урок-{selected_unit} tugadi!\n"
        f"Siz {int(progress['correct'])} ta so‘zni to‘g‘ri topdingiz.\n"
        f"Jami: {get_score_summary({'correct': int(progress['correct']), 'total': int(progress['total'])})}"
    )
    context.user_data.pop("selected_unit", None)
    context.user_data.pop("current_word", None)
    context.user_data.pop("unit_score", None)
    await send_topics(update, context)


async def check_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.message.text:
        return

    word = context.user_data.pop("current_word", None)
    if not word:
        await update.message.reply_text(
            "Avval yangi so‘z olish uchun /random buyrug‘ini yuboring.",
            reply_markup=KEYBOARD,
        )
        return

    is_correct = normalize_answer(update.message.text) in accepted_answers(word["uz"])
    if is_correct:
        result = "✅ To‘g‘ri!"
    else:
        result = f"❌ Noto‘g‘ri. To‘g‘ri javob: {word['uz']}"

    progress = unit_progress(context)
    if progress is not None:
        word_key = get_word_key(word)
        if word_key not in progress["seen"]:
            progress["seen"].add(word_key)
            record_answer(progress, is_correct)
        if len(progress["seen"]) >= len(
            context.application.bot_data["units"].get(context.user_data.get("selected_unit"), {}).get("words", [])
        ):
            await update.message.reply_text(
                f"🎉 урок-{context.user_data.get('selected_unit')} tugadi!\n"
                f"Siz {int(progress['correct'])} ta so‘zni to‘g‘ri topdingiz.\n"
                f"Jami: {get_score_summary(progress)}"
            )
            await finish_unit(update, context)
            return

    pos = word.get("pos")
    description = word.get("description")
    details = [result]
    if progress is not None:
        details.append(get_score_summary(progress))
    if pos:
        details.append(f"📝 So‘z turkumi: {pos}")
    if description:
        details.append(f"💡 Izoh: {description}")
    await update.message.reply_text("\n".join(details))

    await send_random_word(update, context)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi. Telegram bot tokenini BOT_TOKEN "
            "muhit o‘zgaruvchisiga kiriting."
        )

    dictionary_path = Path(
        os.environ.get("WORDS_FILE", Path(__file__).with_name("vocabulary_units.json"))
    )
    words, units = load_words(dictionary_path)
    LOGGER.info("%d ta lug‘at so‘zi yuklandi.", len(words))

    application = Application.builder().token(token).build()
    application.bot_data["words"] = words
    application.bot_data["units"] = units
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("random", send_global_random_word))
    application.add_handler(CallbackQueryHandler(select_unit, pattern=r"^unit:\d+$"))
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(f"^{RANDOM_WORD_BUTTON}$"),
            send_global_random_word,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(f"^{TOPICS_BUTTON}$"),
            topics_button,
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer)
    )
    threading.Thread(target=run_web, daemon=True).start()
    application.run_polling()


if __name__ == "__main__":
    main()
