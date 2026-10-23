import os
import logging
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import uvicorn

TOKEN = "8996066457:AAH0ZitJaV50VhjbbM4mvhYK7fOcEqXPcOU"
bot = Bot(token=TOKEN)
dp = Dispatcher()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

WEBHOOK_URL = "https://sizning-domen.onrender.com"

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 Do'konni ochish",
                    web_app=WebAppInfo(url=f"{WEBHOOK_URL}/shop")
                )
            ]
        ]
    )
    await message.answer(
        "Assalomu alaykum! Bizning internet-do'konimizga xush kelibsiz. "
        "Mahsulotlarni tanlash uchun quyidagi tugmani bosing:",
        reply_markup=keyboard
    )

@app.get("/shop", response_class=HTMLResponse)
async def shop_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/order")
async def create_order(request: Request):
    data = await request.json()
    user_cart = data.get("cart", [])
    total_price = data.get("total", 0)
    
    order_text = f"🚨 Yangi buyurtma!\n\nUmumiy summa: {total_price} so'm\n"
    return {"status": "success", "message": "Buyurtma qabul qilindi!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
