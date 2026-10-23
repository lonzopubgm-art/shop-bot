import io
import os
import re
import json
import time
import hmac
import html
import hashlib
import asyncio
import logging
from collections import OrderedDict, defaultdict, deque
from contextlib import asynccontextmanager, suppress
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.types import (
    WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

# ====================== SOZLAMALAR ======================
TOKEN = os.getenv("TOKEN", "8996066457:AAHJ1IAjw7GrdXcJsfnKXWvBuSDFrAvSYbY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5200431835"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://shop-bot-2-8bi5.onrender.com").rstrip("/")

# Render Disk ulangan bo'lsa, DATA_DIR=/data qiling: ma'lumotlar o'chib ketmaydi.
DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, "products.json")
ORDERS_LOG = os.path.join(DATA_DIR, "orders.jsonl")

# 1 bo'lsa, Telegram initData imzosi bo'lmagan buyurtmalar rad etiladi.
REQUIRE_INITDATA = os.getenv("REQUIRE_INITDATA", "0") == "1"

ORDER_LIMIT = 5          # bir IP dan
ORDER_WINDOW = 60        # shuncha soniyada
MAX_CART_ITEMS = 50

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ====================== TOVARLAR BAZASI ======================
DEFAULT_PRODUCTS = [
    {"id": 1, "name": "Klassik ko'ylak", "cat": "Ko'ylak", "price": 180000, "emoji": "👔", "img": "",
     "sizes": ["S", "M", "L", "XL"], "colors": ["Oq", "Qora", "Ko'k"]},
    {"id": 2, "name": "Slim fit shim", "cat": "Shim", "price": 220000, "emoji": "👖", "img": "",
     "sizes": ["30", "32", "34", "36"], "colors": ["Qora", "Kulrang"]},
    {"id": 3, "name": "Qishki kurtka", "cat": "Kurtka", "price": 650000, "emoji": "🧥", "img": "",
     "sizes": ["M", "L", "XL", "XXL"], "colors": ["Qora", "To'q yashil"]},
    {"id": 4, "name": "Charm poyabzal", "cat": "Poyabzal", "price": 380000, "emoji": "👞", "img": "",
     "sizes": ["40", "41", "42", "43", "44"], "colors": ["Qora", "Jigarrang"]},
]

db_lock = asyncio.Lock()


def validate_products(items):
    """Tovarlar ro'yxatini tekshiradi va to'ldiradi. Xato bo'lsa ValueError."""
    if not isinstance(items, list):
        raise ValueError("ro'yxat emas")
    clean, seen = [], set()
    for p in items:
        if not isinstance(p, dict):
            raise ValueError("tovar obyekt emas")
        pid, price = p.get("id"), p.get("price")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid in seen:
            raise ValueError(f"noto'g'ri yoki takror id: {pid}")
        if not isinstance(price, int) or isinstance(price, bool) or price < 0:
            raise ValueError(f"noto'g'ri narx (id {pid})")
        if not isinstance(p.get("name"), str) or not p["name"].strip():
            raise ValueError(f"nom yo'q (id {pid})")
        seen.add(pid)
        clean.append({
            "id": pid,
            "name": p["name"].strip(),
            "cat": str(p.get("cat", "")).strip(),
            "price": price,
            "emoji": str(p.get("emoji", "🛍️")),
            "img": str(p.get("img", "")),
            "sizes": [str(x) for x in p.get("sizes", [])],
