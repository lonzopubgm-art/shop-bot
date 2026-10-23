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
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/shop", response_class=HTMLResponse)
async def shop_page(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/order")
async def create_order(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Noto'g'ri so'rov"}, status_code=400)

    cart = data.get("cart", [])
    total = data.get("total", 0)
    user = data.get("user") or {}

    lines = []
    for item in cart:
        name = item.get("name") or item.get("title") or "Mahsulot"
        qty = item.get("qty") or item.get("quantity") or 1
        price = item.get("price", "")
        size = item.get("size")
        line = f"• {name} x{qty}"
        if size:
            line += f" ({size})"
        if price != "":
            line += f" - {price} so'm"
        lines.append(line)

    customer = ""
    if user:
        uname = user.get("username")
        customer = (
            f"\n👤 {user.get('first_name', '')} "
            f"{'@' + uname if uname else ''} (ID: {user.get('id', '-')})"
        )

    order_text = (
        "🚨 Yangi buyurtma!\n\n"
        + ("\n".join(lines) if lines else "Savat bo'sh")
        + f"\n\n💰 Umumiy summa: {total} so'm"
        + customer
    )
    logging.info(order_text)

    try:
        await bot.send_message(ADMIN_ID, order_text)
    except Exception:
        logging.exception("Adminga xabar yuborib bo'lmadi")
        return JSONResponse({"status": "error", "message": "Xatolik, qayta urinib ko'ring"}, status_code=500)

    return {"status": "success", "message": "Buyurtma qabul qilindi!"}
