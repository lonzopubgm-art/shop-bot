import os
import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN", "8996066457:AAHJ1IAjw7GrdXcJsfnKXWvBuSDFrAvSYbY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5200431835"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://shop-bot-2-8bi5.onrender.com").rstrip("/")

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 Do'konni ochish",
                    web_app=WebAppInfo(url=f"{WEBHOOK_URL}/shop"),
                )
            ]
        ]
    )
    await message.answer(
        "Assalomu alaykum! Bizning internet-do'konimizga xush kelibsiz. "
        "Mahsulotlarni tanlash uchun quyidagi tugmani bosing:",
        reply_markup=keyboard,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.delete_webhook(drop_pending_updates=True)
    task = asyncio.create_task(dp.start_polling(bot))
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    await bot.session.close()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templat
