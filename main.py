import io
import os
import re
import json
import asyncio
import logging
from collections import OrderedDict
from contextlib import asynccontextmanager, suppress
from pathlib import Path

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

BASE_DIR = Path(__file__).resolve().parent

TOKEN = os.getenv("TOKEN", "8996066457:AAHJ1IAjw7GrdXcJsfnKXWvBuSDFrAvSYbY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5200431835"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://shop-bot-2-8bi5.onrender.com").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "shopbot_secret_2026")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ====================== TOVARLAR BAZASI ======================
DB = str(BASE_DIR / "products.json")
db_lock = asyncio.Lock()

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


def load_products():
    if not os.path.exists(DB):
        return list(DEFAULT_PRODUCTS)
    try:
        with open(DB, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else list(DEFAULT_PRODUCTS)
    except Exception:
        logging.exception("products.json o'qilmadi")
        return list(DEFAULT_PRODUCTS)


async def save_products(items):
    data = json.dumps(items, ensure_ascii=False, indent=2)
    async with db_lock:
        with open(DB, "w", encoding="utf-8") as f:
            f.write(data)
    try:
        await bot.send_document(
            ADMIN_ID,
            BufferedInputFile(data.encode("utf-8"), filename="products.json"),
            caption="💾 Zaxira nusxa. Server tozalanib qolsa, shu faylni botga yuboring.",
        )
    except Exception:
        logging.exception("Zaxira yuborilmadi")


def split(text):
    return [x.strip() for x in text.split(",") if x.strip()]


def to_int(value, default=0):
    digits = re.sub(r"\D", "", str(value or ""))
    return int(digits) if digits else default


def money(n):
    return f"{int(n):,}".replace(",", " ")


# ====================== ADMIN BUYRUQLARI ======================
admin = Router()
admin.message.filter(F.from_user.id == ADMIN_ID)


class Add(StatesGroup):
    name = State()
    price = State()
    cat = State()
    sizes = State()
    colors = State()
    photo = State()


@admin.message(Command("cancel"))
async def cancel(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("Bekor qilindi.")


@admin.message(Command("help"))
async def admin_help(m: types.Message):
    await m.answer(
        "Admin buyruqlari:\n"
        "/add - yangi tovar qo'shish\n"
        "/list - tovarlar ro'yxati\n"
        "/del ID - tovarni o'chirish\n"
        "/cancel - bekor qilish\n\n"
        "products.json faylini yuborsangiz, baza tiklanadi."
    )


@admin.message(Command("add"))
async def add_start(m: types.Message, state: FSMContext):
    await state.set_state(Add.name)
    await m.answer("Tovar nomi? (bekor qilish: /cancel)")


@admin.message(Add.name, F.text)
async def add_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(Add.price)
    await m.answer("Narxi? (faqat raqam, masalan 180000)")


@admin.message(Add.price, F.text)
async def add_price(m: types.Message, state: FSMContext):
    price = to_int(m.text)
    if price <= 0:
        return await m.answer("Faqat raqam yozing, masalan 180000")
    await state.update_data(price=price)
    await state.set_state(Add.cat)
    await m.answer("Kategoriya? (masalan: Ko'ylak, Shim, Kurtka, Poyabzal)")


@admin.message(Add.cat, F.text)
async def add_cat(m: types.Message, state: FSMContext):
    await state.update_data(cat=m.text.strip())
    await state.set_state(Add.sizes)
    await m.answer("Razmerlar? Vergul bilan: S, M, L, XL")


@admin.message(Add.sizes, F.text)
async def add_sizes(m: types.Message, state: FSMContext):
    sizes = split(m.text)
    if not sizes:
        return await m.answer("Kamida bitta razmer yozing.")
    await state.update_data(sizes=sizes)
    await state.set_state(Add.colors)
    await m.answer("Ranglar? Vergul bilan: Oq, Qora, Ko'k")


@admin.message(Add.colors, F.text)
async def add_colors(m: types.Message, state: FSMContext):
    colors = split(m.text)
    if not colors:
        return await m.answer("Kamida bitta rang yozing.")
    await state.update_data(colors=colors)
    await state.set_state(Add.photo)
    await m.answer("Endi tovar rasmini yuboring (oddiy foto sifatida).")


@admin.message(Add.photo, F.photo)
async def add_photo(m: types.Message, state: FSMContext):
    data = await state.get_data()
    file_id = m.photo[-1].file_id
    items = load_products()
    new_id = max([p["id"] for p in items], default=0) + 1
    items.append({
        "id": new_id,
        "name": data["name"],
        "cat": data["cat"],
        "price": data["price"],
        "emoji": "🛍️",
        "img": f"/api/img/{file_id}",
        "sizes": data["sizes"],
        "colors": data["colors"],
    })
    await save_products(items)
    await state.clear()
    await m.answer(f"✅ Qo'shildi: {data['name']} (ID: {new_id})")


@admin.message(Add.photo)
async def add_photo_wrong(m: types.Message):
    await m.answer("Iltimos, rasm yuboring (fayl emas, oddiy foto).")


@admin.message(Command("list"))
async def list_products(m: types.Message):
    items = load_products()
    if not items:
        return await m.answer("Tovarlar yo'q.")
    text = "\n".join(
        f"{p['id']}. {p['name']} — {money(p['price'])} so'm [{p['cat']}]" for p in items
    )
    await m.answer(text + "\n\nO'chirish: /del ID")


@admin.message(Command("del"))
async def delete_product(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.answer("Ishlatilishi: /del 3")
    pid = int(parts[1])
    items = load_products()
    left = [p for p in items if p["id"] != pid]
    if len(left) == len(items):
        return await m.answer("Bunday ID topilmadi.")
    await save_products(left)
    await m.answer("🗑 O'chirildi.")


@admin.message(F.document)
async def restore(m: types.Message):
    if m.document.file_name != "products.json":
        return
    try:
        buf = io.BytesIO()
        await bot.download(m.document, destination=buf)
        items = json.loads(buf.getvalue().decode("utf-8"))
        assert isinstance(items, list)
        async with db_lock:
            with open(DB, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        await m.answer(f"♻️ Tiklandi: {len(items)} ta tovar.")
    except Exception:
        logging.exception("Tiklashda xatolik")
        await m.answer("Fayl noto'g'ri.")


dp.include_router(admin)


# ====================== START ======================
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
    if message.from_user and message.from_user.id == ADMIN_ID:
        await message.answer("Siz adminsiz. Buyruqlar ro'yxati: /help")


# ====================== SERVER ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(
        f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
        allowed_updates=dp.resolve_used_update_types(),
    )
    logging.info("Webhook o'rnatildi: %s%s", WEBHOOK_URL, WEBHOOK_PATH)
    yield
    with suppress(Exception):
        await bot.session.close()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "ok"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return Response(status_code=403)
    try:
        update = types.Update.model_validate(await request.json(), context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception:
        logging.exception("Update ishlanmadi")
    return {"ok": True}


@app.get("/shop", response_class=HTMLResponse)
async def shop_page(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/products")
async def api_products():
    return JSONResponse(load_products(), headers={"Cache-Control": "no-store"})


IMG_CACHE: "OrderedDict[str, bytes]" = OrderedDict()
IMG_CACHE_MAX = 100


@app.get("/api/img/{file_id}")
async def api_img(file_id: str):
    headers = {"Cache-Control": "public, max-age=86400"}
    if file_id in IMG_CACHE:
        IMG_CACHE.move_to_end(file_id)
        return Response(IMG_CACHE[file_id], media_type="image/jpeg", headers=headers)
    try:
        f = await bot.get_file(file_id)
        buf = io.BytesIO()
        await bot.download_file(f.file_path, destination=buf)
        content = buf.getvalue()
        IMG_CACHE[file_id] = content
        if len(IMG_CACHE) > IMG_CACHE_MAX:
            IMG_CACHE.popitem(last=False)
        return Response(content, media_type="image/jpeg", headers=headers)
    except Exception:
        return Response(status_code=404)


@app.post("/api/order")
async def create_order(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Noto'g'ri so'rov"}, status_code=400)

    cart = data.get("cart") or []
    if not isinstance(cart, list) or not cart:
        return JSONResponse({"status": "error", "message": "Savat bo'sh"}, status_code=400)
    cart = cart[:50]

    user = data.get("user") or {}
    products = {p["id"]: p for p in load_products()}

    lines = []
    total = 0
    for item in cart:
        if not isinstance(item, dict):
            continue
        pid = to_int(item.get("id"), default=-1)
        prod = products.get(pid)

        name = prod["name"] if prod else (item.get("name") or item.get("title") or "Mahsulot")
        qty = min(max(to_int(item.get("qty") or item.get("quantity"), 1), 1), 99)
        # Narx serverdagi bazadan olinadi (mijoz yuborgan narxga ishonilmaydi)
        price = prod["price"] if prod else to_int(item.get("price"))
        total += price * qty

        line = f"• {name} x{qty}"
        extras = [str(x) for x in (item.get("size"), item.get("color")) if x]
        if extras:
            line += f" ({', '.join(extras)})"
        if price:
            line += f" - {money(price * qty)} so'm"
        lines.append(line)

    if not lines:
        return JSONResponse({"status": "error", "message": "Savat bo'sh"}, status_code=400)

    customer = ""
    if isinstance(user, dict) and user:
        uname = user.get("username")
        customer = (
            f"\n👤 {user.get('first_name', '')} "
            f"{'@' + uname if uname else ''} (ID: {user.get('id', '-')})"
        )

    order_text = (
        "🚨 Yangi buyurtma!\n\n"
        + "\n".join(lines)
        + f"\n\n💰 Umumiy summa: {money(total)} so'm"
        + customer
    )
    logging.info(order_text)

    try:
        await bot.send_message(ADMIN_ID, order_text)
    except Exception:
        logging.exception("Adminga xabar yuborib bo'lmadi")
        return JSONResponse({"status": "error", "message": "Xatolik, qayta urinib ko'ring"}, status_code=500)

    return {"status": "success", "message": "Buyurtma qabul qilindi!"}
