import io
import os
import re
import json
import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, Response
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.types import (
    WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN", "8996066457:AAHJ1IAjw7GrdXcJsfnKXWvBuSDFrAvSYbY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5200431835"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://shop-bot-2-8bi5.onrender.com").rstrip("/")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ====================== TOVARLAR BAZASI ======================
DB = "products.json"

DEFAULT_PRODUCTS = [
    {"id": 1, "name": "Klassik ko'ylak", "cat": "Ko'ylak", "price": 180000, "emoji
