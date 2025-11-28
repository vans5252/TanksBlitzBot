a# bot.py
import asyncio
import json
import httpx
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

BOT_TOKEN = "8567793904:AAEpdovaNgQJtHQNpz0CowSIWE5EU7S8vvU"  # ← Замени!
WEB_APP_URL = "https://tanksblitzbot.onrender.com/"  # ← Ссылка на твой Web App

router = Router()

async def get_account_id_by_nickname(nickname: str) -> int | None:
    """Возвращает account_id по нику, или None, если не найден."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "https://papi.tanksblitz.ru/wotb/account/list/",
                params={"search": nickname},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = resp.json()
            if data.get("status") == "ok" and data.get("data"):
                # Ищем точное совпадение (регистр важен!)
                for user in data["data"]:
                    if user["nickname"] == nickname:
                        return int(user["account_id"])
                # Если точного нет — берём первый
                return int(data["data"][0]["account_id"])
        except Exception:
            pass
    return None

async def get_tank_stats(account_id: int) -> dict | None:
    """Возвращает статистику по account_id."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "https://papi.tanksblitz.ru/wotb/account/tankstats/",
                params={"account_id": account_id},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = resp.json()
            if data.get("status") == "ok" and str(account_id) in data.get("data", {}):
                return data["data"][str(account_id)]
        except Exception:
            pass
    return None

@router.message(Command("start"))
async def start_cmd(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📈 Проверить статистику по нику",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )]
    ])
    await message.answer(
        "Привет! Нажми кнопку, чтобы проверить статистику по нику в Tanks Blitz.",
        reply_markup=kb
    )

# Обработка данных из Web App (пользователь прислал ник)
@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        payload = json.loads(message.web_app_data.data)
        nickname = payload["nickname"].strip()
        if not nickname:
            raise ValueError()
    except (json.JSONDecodeError, KeyError, ValueError):
        await message.answer("❌ Неверный формат данных.")
        return

    await message.answer(f"🔍 Ищу аккаунт: <b>{nickname}</b>...", parse_mode="HTML")

    account_id = await get_account_id_by_nickname(nickname)
    if not account_id:
        await message.answer("❌ Игрок с таким ником не найден.")
        return

    stats = await get_tank_stats(account_id)
    if not stats or "all" not in stats:
        await message.answer("❌ Статистика недоступна.")
        return

    all_stats = stats["all"]
    battles = all_stats.get("battles", 0)
    wins = all_stats.get("wins", 0)
    dmg = all_stats.get("damage_dealt", 0)
    winrate = round(wins / battles * 100, 2) if battles else 0

    msg = (
        f"📊 Игрок: <b>{nickname}</b>\n"
        f"🆔 ID: <code>{account_id}</code>\n\n"
        f"🎮 Боёв: {battles}\n"
        f"🏆 Побед: {wins} ({winrate}%)\n"
        f"💥 Урон: {dmg}"
    )
    await message.answer(msg, parse_mode="HTML")

# Альтернатива: ввод ника прямо в чате (без Web App)
@router.message(Command("stats"))
async def stats_by_nickname(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используй: /stats Имя_Игрока")
        return

    nickname = parts[1].strip()
    await message.answer(f"🔍 Ищу: <b>{nickname}</b>...", parse_mode="HTML")

    account_id = await get_account_id_by_nickname(nickname)
    if not account_id:
        await message.answer("❌ Игрок не найден.")
        return

    stats = await get_tank_stats(account_id)
    if not stats:
        await message.answer("❌ Ошибка загрузки статистики.")
        return

    all_stats = stats["all"]
    battles = all_stats.get("battles", 0)
    wins = all_stats.get("wins", 0)
    winrate = round(wins / battles * 100, 2) if battles else 0

    msg = (
        f"📊 <b>{nickname}</b>\n"
        f"🎮 Боёв: {battles}\n"
        f"🏆 Побед: {wins} ({winrate}%)"
    )
    await message.answer(msg, parse_mode="HTML")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
