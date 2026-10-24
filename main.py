import io
import os
import re
import json
import time
import hmac
import hashlib
import secrets
import asyncio
import logging
from collections import OrderedDict
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl

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

# ====================== SOZLAMALAR (hammasi Render Environment'dan) ======================
TOKEN = os.environ["TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://shop-bot-2-8bi5.onrender.com").rstrip("/")
WEBHOOK_PATH = "/webhook"
# Telegram imzosi tekshirilsin (soxta buyurtmalardan himoya). Render'da STRICT_ORDERS=1
STRICT_ORDERS = os.getenv("STRICT_ORDERS") == "1"
# Ishchilarning Telegram ID raqamlari, vergul bilan: 712345678,723456789
SELLER_IDS = {int(x) for x in re.findall(r"\d+", os.getenv("SELLER_IDS", ""))}
STAFF_IDS = SELLER_IDS | {ADMIN_ID}
LOW_STOCK = 2  # shu sondan kam qolsa adminga ogohlantirish
TZ = timezone(timedelta(hours=5))  # Toshkent vaqti

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ====================== MA'LUMOTLAR BAZASI (JSON fayllar) ======================
DB = os.getenv("DB_PATH", str(BASE_DIR / "products.json"))
DATA_DIR = Path(DB).parent
ORDERS_DB = str(DATA_DIR / "orders.json")
SALES_DB = str(DATA_DIR / "sales.json")
with suppress(Exception):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

db_lock = asyncio.Lock()  # tovar/buyurtma/sotuvni o'zgartirishda faqat bitta kishi

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


def clean_products(items):
    """Bazani tekshiradi. Noto'g'ri bo'lsa xatolik beradi."""
    if not isinstance(items, list):
        raise ValueError("ro'yxat emas")
    out = []
    for p in items:
        out.append({
            "id": int(p["id"]),
            "name": str(p["name"]),
            "cat": str(p.get("cat", "")),
            "price": int(p["price"]),
            "emoji": str(p.get("emoji", "🛍️")),
            "img": str(p.get("img", "")),
            "sizes": [str(x) for x in p.get("sizes", [])],
            "colors": [str(x) for x in p.get("colors", [])],
            # qoldiq: {"M|Qora": 5}. Kaliti yo'q bo'lsa, qoldiq hisoblanmaydi (cheksiz)
            "stock": {str(k): int(v) for k, v in (p.get("stock") or {}).items()},
        })
    return out


def read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logging.exception("%s o'qilmadi", path)
        return default


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def write_db(items):
    write_json(DB, items)


def load_products():
    if not os.path.exists(DB):
        return clean_products(DEFAULT_PRODUCTS)
    try:
        with open(DB, encoding="utf-8") as f:
            return clean_products(json.load(f))
    except Exception:
        logging.exception("products.json o'qilmadi")
        return clean_products(DEFAULT_PRODUCTS)


def load_orders():
    data = read_json(ORDERS_DB, [])
    return data if isinstance(data, list) else []


def load_sales():
    data = read_json(SALES_DB, [])
    return data if isinstance(data, list) else []


def find_product(products, pid):
    return next((p for p in products if p["id"] == pid), None)


async def pin_only(message_id):
    """Eski qadalgan xabarlarni olib, faqat yangisini qadaydi."""
    with suppress(Exception):
        await bot.unpin_all_chat_messages(ADMIN_ID)
    await bot.pin_chat_message(ADMIN_ID, message_id, disable_notification=True)


async def send_backup(items):
    """Tovarlar zaxirasini adminga yuboradi va qadaydi (faqat admin o'zgartirganda)."""
    data = json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        sent = await bot.send_document(
            ADMIN_ID,
            BufferedInputFile(data, filename="products.json"),
            caption="💾 Zaxira nusxa. Server qayta ishga tushganda avtomatik tiklanadi.",
        )
        await pin_only(sent.message_id)
    except Exception:
        logging.exception("Zaxira yuborilmadi")


async def restore_from_pinned():
    """Server tozalangan bo'lsa, admin chatida qadalgan products.json dan tiklaydi."""
    try:
        chat = await bot.get_chat(ADMIN_ID)
        pinned = getattr(chat, "pinned_message", None)
        doc = pinned.document if pinned else None
        if not doc or doc.file_name != "products.json":
            logging.info("Qadalgan zaxira topilmadi, standart tovarlar ishlatiladi")
            return
        buf = io.BytesIO()
        await bot.download(doc, destination=buf)
        items = clean_products(json.loads(buf.getvalue().decode("utf-8")))
        write_db(items)
        logging.info("Baza qadalgan zaxiradan tiklandi: %s ta tovar", len(items))
    except Exception:
        logging.exception("Zaxiradan tiklab bo'lmadi")


# ====================== YORDAMCHI FUNKSIYALAR ======================
def split(text):
    return [x.strip() for x in text.split(",") if x.strip()]


def to_int(value, default=0):
    digits = re.sub(r"\D", "", str(value or ""))
    return int(digits) if digits else default


def money(n):
    return f"{int(n):,}".replace(",", " ")


def norm(s):
    """Solishtirish uchun: kichik harf, har xil apostroflar bir xil."""
    return re.sub(r"[’‘ʻʼ`´]", "'", str(s)).strip().lower()


def fmt_ts(ts):
    return datetime.fromtimestamp(ts, TZ).strftime("%d.%m %H:%M")


async def send_long(m, text):
    while text:
        if len(text) <= 3800:
            chunk, text = text, ""
        else:
            cut = text.rfind("\n", 0, 3800)
            cut = cut if cut > 0 else 3800
            chunk, text = text[:cut], text[cut:].lstrip("\n")
        await m.answer(chunk)


# ====================== QOLDIQ (ZAXIRA) MANTIG'I ======================
def vkey(size, color):
    return f"{size}|{color}"


def get_stock(prod, size, color):
    """None = qoldiq hisoblanmaydi (cheksiz). Son = qolgan dona."""
    return (prod.get("stock") or {}).get(vkey(size, color))


def reserve(byid, wanted):
    """wanted: {(pid, size, color): qty}. Yetmasa xabar matnini qaytaradi va hech narsani o'zgartirmaydi."""
    for (pid, size, color), qty in wanted.items():
        p = byid[pid]
        left = get_stock(p, size, color)
        if left is not None and left < qty:
            if left <= 0:
                return f"«{p['name']}» ({size}, {color}) tugagan"
            return f"«{p['name']}» ({size}, {color}): faqat {left} ta qoldi"
    for (pid, size, color), qty in wanted.items():
        p = byid[pid]
        left = get_stock(p, size, color)
        if left is not None:
            p["stock"][vkey(size, color)] = left - qty
    return None


def restore_stock(products, items):
    byid = {p["id"]: p for p in products}
    for it in items:
        p = byid.get(it["pid"])
        if not p:
            continue
        key = vkey(it["size"], it["color"])
        if key in (p.get("stock") or {}):
            p["stock"][key] += it["qty"]


def parse_variant(prod, tokens):
    """['M', 'Qora'] yoki ['32', "To'q", 'yashil'] -> (razmer, rang). Topilmasa None."""
    sizes = prod["sizes"] or ["Standart"]
    colors = prod["colors"] or ["Standart"]
    if len(tokens) < 2:
        return None, None
    size = next((s for s in sizes if norm(s) == norm(tokens[0])), None)
    color = next((c for c in colors if norm(c) == norm(" ".join(tokens[1:]))), None)
    return size, color


def split_qty(tokens, default=1):
    """Oxirgi element raqam bo'lsa, u soni."""
    if len(tokens) >= 3 and tokens[-1].isdigit():
        return tokens[:-1], int(tokens[-1])
    return tokens, default


def public_product(p):
    """Mijozga ko'rsatiladigan ko'rinish: aniq qoldiq yashiriladi, faqat tugagan/kam qolgani."""
    stock = p.get("stock") or {}
    sizes = p["sizes"] or ["Standart"]
    colors = p["colors"] or ["Standart"]
    out, low, avail = [], {}, False
    for s in sizes:
        for c in colors:
            left = stock.get(vkey(s, c))
            if left is None or left > 0:
                avail = True
            if left is not None and left <= 0:
                out.append(vkey(s, c))
            elif left is not None and left <= 3:
                low[vkey(s, c)] = left
    d = {k: v for k, v in p.items() if k != "stock"}
    d.update(out=out, low=low, soldout=not avail)
    return d


def low_text(entries):
    """entries: [(nom, razmer, rang, qoldiq)]"""
    if not entries:
        return ""
    lines = []
    for name, size, color, left in entries:
        lines.append(f"• {name} ({size}, {color}): " + ("tugadi" if left <= 0 else f"{left} ta qoldi"))
    return "⚠️ Kam qoldi:\n" + "\n".join(lines)


# ====================== BUYURTMA MATNI VA TUGMALAR ======================
STATUS = {
    "new": "🆕 Yangi",
    "confirmed": "✅ Tasdiqlandi",
    "shipping": "🚚 Yo'lda",
    "delivered": "📦 Yetkazildi",
    "cancelled": "❌ Bekor qilindi",
}
NEXT = {
    "new": ("confirmed", "✅ Tasdiqlash"),
    "confirmed": ("shipping", "🚚 Yo'lda"),
    "shipping": ("delivered", "📦 Yetkazildi"),
}
CUSTOMER_MSG = {
    "confirmed": "✅ Buyurtmangiz #{id} tasdiqlandi.",
    "shipping": "🚚 Buyurtmangiz #{id} yo'lga chiqdi.",
    "delivered": "📦 Buyurtmangiz #{id} yetkazildi. Xaridingiz uchun rahmat!",
    "cancelled": "❌ Buyurtmangiz #{id} bekor qilindi. Savollar bo'lsa, biz bilan bog'laning.",
}


def order_text(o):
    lines = [
        f"• {i['name']} x{i['qty']} ({i['size']}, {i['color']}) - {money(i['price'] * i['qty'])} so'm"
        for i in o["items"]
    ]
    parts = [f"🚨 Buyurtma #{o['id']}  |  {STATUS.get(o['status'], o['status'])}", ""]
    parts += lines
    parts += ["", f"💰 Umumiy summa: {money(o['total'])} so'm", ""]
    if o.get("verified"):
        uname = o.get("tg_username")
        parts.append(f"👤 {o.get('tg_name', '')} {'@' + uname if uname else ''} (ID: {o.get('user_id')})")
    else:
        parts.append("⚠️ Mijoz Telegram orqali tasdiqlanmagan")
    if o.get("name"):
        parts.append(f"🙋 {o['name']}")
    if o.get("phone"):
        parts.append(f"📞 {o['phone']}")
    if o.get("address"):
        parts.append(f"📍 {o['address']}")
    parts.append(f"🕒 {fmt_ts(o['ts'])}")
    return "\n".join(parts)


def order_kb(o):
    st = o["status"]
    row = []
    if st in NEXT:
        row.append(InlineKeyboardButton(text=NEXT[st][1], callback_data=f"o:{o['id']}:{NEXT[st][0]}"))
    if st in ("new", "confirmed", "shipping"):
        row.append(InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"o:{o['id']}:cancelled"))
    return InlineKeyboardMarkup(inline_keyboard=[row]) if row else None


def build_report(orders, sales, days=1):
    now = datetime.now(TZ)
    start = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()) - (days - 1) * 86400
    on = [o for o in orders if o["ts"] >= start and o["status"] != "cancelled"]
    off = [s for s in sales if s["ts"] >= start]
    on_sum = sum(o["total"] for o in on)
    off_sum = sum(s["price"] * s["qty"] for s in off)
    on_units = sum(i["qty"] for o in on for i in o["items"])
    off_units = sum(s["qty"] for s in off)
    top = {}
    for o in on:
        for i in o["items"]:
            top[i["name"]] = top.get(i["name"], 0) + i["qty"]
    for s in off:
        top[s["name"]] = top.get(s["name"], 0) + s["qty"]
    title = "bugun" if days == 1 else f"oxirgi {days} kun"
    text = (
        f"📊 Hisobot ({title})\n\n"
        f"🌐 Onlayn: {len(on)} ta buyurtma, {on_units} dona, {money(on_sum)} so'm\n"
        f"🏬 Do'kon: {off_units} dona, {money(off_sum)} so'm\n"
        f"💰 Jami: {money(on_sum + off_sum)} so'm\n"
        "(bekor qilingan buyurtmalar hisobga olinmagan)"
    )
    if top:
        best = sorted(top.items(), key=lambda x: -x[1])[:5]
        text += "\n\n🔥 Eng ko'p sotilgan:\n" + "\n".join(f"{n}. {name}: {q} dona" for n, (name, q) in enumerate(best, 1))
    return text


# ====================== XODIMLAR (ADMIN + ISHCHILAR) ======================
staff = Router()
staff.message.filter(F.from_user.id.in_(STAFF_IDS))


@staff.message(Command("help"))
async def help_cmd(m: types.Message):
    if m.from_user.id == ADMIN_ID:
        await m.answer(
            "👑 Admin buyruqlari:\n"
            "/add - yangi tovar qo'shish\n"
            "/list - tovarlar ro'yxati\n"
            "/stock ID - tovar qoldig'i\n"
            "/setstock ID razmer rang soni - qoldiqni o'rnatish\n"
            "/fillstock ID soni - hamma razmer/rangga bir xil son\n"
            "/sold ID razmer rang [soni] - do'kondagi savdo\n"
            "/del ID - tovarni o'chirish\n"
            "/orders - oxirgi buyurtmalar\n"
            "/order KOD - bitta buyurtma\n"
            "/report [kun] - hisobot (masalan /report 7)\n"
            "/sales - bugungi do'kon savdolari\n"
            "/backup - zaxira fayllarni olish\n"
            "/cancel - bekor qilish\n\n"
            "Fayl yuborsangiz (products.json, orders.json, sales.json), baza tiklanadi."
        )
    else:
        await m.answer(
            "Xodim buyruqlari:\n"
            "/list - tovarlar va ID raqamlari\n"
            "/stock ID - tovar qoldig'i\n"
            "/sold ID razmer rang [soni] - sotilganini yozish\n\n"
            "Masalan: /sold 3 M Qora\n"
            "Yoki: /sold 3 M Qora 2"
        )


@staff.message(Command("list"))
async def list_products(m: types.Message):
    items = load_products()
    if not items:
        return await m.answer("Tovarlar yo'q.")
    lines = []
    for p in items:
        stock = p.get("stock") or {}
        tail = f" | qoldiq: {sum(stock.values())}" if stock else ""
        lines.append(f"{p['id']}. {p['name']} — {money(p['price'])} so'm [{p['cat']}]{tail}")
    await send_long(m, "\n".join(lines) + "\n\nQoldiq: /stock ID")


@staff.message(Command("stock"))
async def stock_cmd(m: types.Message):
    args = (m.text or "").split()
    if len(args) != 2 or not args[1].isdigit():
        return await m.answer("Ishlatilishi: /stock 3")
    prod = find_product(load_products(), int(args[1]))
    if not prod:
        return await m.answer("Bunday ID topilmadi. /list")
    lines = [f"📦 {prod['name']} (ID {prod['id']})"]
    for s in prod["sizes"] or ["Standart"]:
        cells = []
        for c in prod["colors"] or ["Standart"]:
            left = get_stock(prod, s, c)
            cells.append(f"{c}: {'∞' if left is None else left}")
        lines.append(f"• {s}  →  " + ", ".join(cells))
    lines.append("\n∞ = qoldiq hisoblanmaydi")
    await send_long(m, "\n".join(lines))


@staff.message(Command("sold"))
async def sold_cmd(m: types.Message):
    args = (m.text or "").split()[1:]
    usage = (
        "Ishlatilishi:\n/sold ID razmer rang [soni]\n"
        "Masalan: /sold 3 M Qora\nYoki: /sold 3 M Qora 2\nID ni bilish: /list"
    )
    if len(args) < 3 or not args[0].isdigit():
        return await m.answer(usage)
    tokens, qty = split_qty(args[1:])
    if not 1 <= qty <= 99:
        return await m.answer("Soni 1 dan 99 gacha bo'lsin.")

    async with db_lock:
        products = load_products()
        prod = find_product(products, int(args[0]))
        if not prod:
            return await m.answer("Bunday ID topilmadi. /list")
        size, color = parse_variant(prod, tokens)
        if not size or not color:
            return await m.answer(
                "Razmer yoki rang noto'g'ri.\n"
                f"Razmerlar: {', '.join(prod['sizes'] or ['Standart'])}\n"
                f"Ranglar: {', '.join(prod['colors'] or ['Standart'])}"
            )
        left = get_stock(prod, size, color)
        if left is not None and left < qty:
            return await m.answer(f"Qoldiq yetmaydi: faqat {left} ta bor.")
        if left is not None:
            prod["stock"][vkey(size, color)] = left - qty
            write_db(products)
        sales = load_sales()
        sales.append({
            "ts": int(time.time()), "by": m.from_user.id, "by_name": m.from_user.full_name,
            "pid": prod["id"], "name": prod["name"], "size": size, "color": color,
            "qty": qty, "price": prod["price"],
        })
        write_json(SALES_DB, sales)
        new_left = None if left is None else left - qty

    text = f"✅ Sotildi: {prod['name']} ({size}, {color}) x{qty}\n"
    text += "Qoldiq hisoblanmaydi (/setstock bilan o'rnating)." if new_left is None else f"Qoldiq: {new_left} ta"
    warn = ""
    if new_left is not None and new_left <= LOW_STOCK:
        warn = low_text([(prod["name"], size, color, new_left)])
    if warn and m.from_user.id == ADMIN_ID:
        text += "\n\n" + warn
    await m.answer(text)
    if warn and m.from_user.id != ADMIN_ID:
        with suppress(Exception):
            await bot.send_message(ADMIN_ID, warn + f"\n(sotuvchi: {m.from_user.full_name})")


dp.include_router(staff)


# ====================== ADMIN BUYRUQLARI ======================
admin = Router()
admin.message.filter(F.from_user.id == ADMIN_ID)
admin.callback_query.filter(F.from_user.id == ADMIN_ID)


class Add(StatesGroup):
    name = State()
    price = State()
    cat = State()
    sizes = State()
    colors = State()
    stock = State()
    photo = State()


@admin.message(Command("cancel"))
async def cancel(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("Bekor qilindi.")


@admin.message(Command("add"))
async def add_start(m: types.Message, state: FSMContext):
    await state.set_state(Add.name)
    await m.answer("Tovar nomi? (bekor qilish: /cancel)")


# Buyruqlar (/list, /del ...) nom sifatida qabul qilinmasligi uchun "/" bilan boshlanmaganlar olinadi
@admin.message(Add.name, F.text.regexp(r"^[^/]"))
async def add_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(Add.price)
    await m.answer("Narxi? (faqat raqam, masalan 180000)")


@admin.message(Add.price, F.text.regexp(r"^[^/]"))
async def add_price(m: types.Message, state: FSMContext):
    price = to_int(m.text)
    if price <= 0:
        return await m.answer("Faqat raqam yozing, masalan 180000")
    await state.update_data(price=price)
    await state.set_state(Add.cat)
    await m.answer("Kategoriya? (masalan: Ko'ylak, Shim, Kurtka, Poyabzal)")


@admin.message(Add.cat, F.text.regexp(r"^[^/]"))
async def add_cat(m: types.Message, state: FSMContext):
    await state.update_data(cat=m.text.strip())
    await state.set_state(Add.sizes)
    await m.answer("Razmerlar? Vergul bilan: S, M, L, XL (shim uchun: 30, 32, 34, 36)")


@admin.message(Add.sizes, F.text.regexp(r"^[^/]"))
async def add_sizes(m: types.Message, state: FSMContext):
    sizes = split(m.text)
    if not sizes:
        return await m.answer("Kamida bitta razmer yozing.")
    await state.update_data(sizes=sizes)
    await state.set_state(Add.colors)
    await m.answer("Ranglar? Vergul bilan: Oq, Qora, Ko'k")


@admin.message(Add.colors, F.text.regexp(r"^[^/]"))
async def add_colors(m: types.Message, state: FSMContext):
    colors = split(m.text)
    if not colors:
        return await m.answer("Kamida bitta rang yozing.")
    await state.update_data(colors=colors)
    await state.set_state(Add.stock)
    await m.answer(
        "Har bir razmer va rang uchun nechta dona bor? Bir xil son yozing (masalan 5).\n"
        "Keyin /setstock bilan alohida o'zgartirsa bo'ladi.\n"
        "Qoldiqni hisoblamaslik uchun - (tire) yozing."
    )


@admin.message(Add.stock, F.text.regexp(r"^[^/]"))
async def add_stock(m: types.Message, state: FSMContext):
    t = m.text.strip()
    if t == "-":
        await state.update_data(stock=None)
    elif t.isdigit() and int(t) <= 100000:
        await state.update_data(stock=int(t))
    else:
        return await m.answer("Faqat raqam yozing (masalan 5) yoki - (tire).")
    await state.set_state(Add.photo)
    await m.answer("Endi tovar rasmini yuboring (oddiy foto sifatida).")


@admin.message(Add.photo, F.photo)
async def add_photo(m: types.Message, state: FSMContext):
    data = await state.get_data()
    file_id = m.photo[-1].file_id
    n = data.get("stock")
    stock = {}
    if n is not None:
        stock = {vkey(s, c): n for s in data["sizes"] for c in data["colors"]}
    async with db_lock:
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
            "stock": stock,
        })
        write_db(items)
    await state.clear()
    await m.answer(f"✅ Qo'shildi: {data['name']} (ID: {new_id})")
    await send_backup(items)


@admin.message(Command("del"))
async def delete_product(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.answer("Ishlatilishi: /del 3")
    pid = int(parts[1])
    async with db_lock:
        items = load_products()
        left = [p for p in items if p["id"] != pid]
        if len(left) == len(items):
            return await m.answer("Bunday ID topilmadi.")
        write_db(left)
    await m.answer("🗑 O'chirildi.")
    await send_backup(left)


@admin.message(Command("setstock"))
async def setstock_cmd(m: types.Message):
    args = (m.text or "").split()[1:]
    usage = "Ishlatilishi: /setstock ID razmer rang soni\nMasalan: /setstock 3 M Qora 10\nHisoblamaslik: /setstock 3 M Qora -"
    if len(args) < 4 or not args[0].isdigit():
        return await m.answer(usage)
    last = args[-1]
    if last == "-":
        value = None
    elif last.isdigit() and int(last) <= 100000:
        value = int(last)
    else:
        return await m.answer(usage)
    async with db_lock:
        products = load_products()
        prod = find_product(products, int(args[0]))
        if not prod:
            return await m.answer("Bunday ID topilmadi. /list")
        size, color = parse_variant(prod, args[1:-1])
        if not size or not color:
            return await m.answer(
                "Razmer yoki rang noto'g'ri.\n"
                f"Razmerlar: {', '.join(prod['sizes'] or ['Standart'])}\n"
                f"Ranglar: {', '.join(prod['colors'] or ['Standart'])}"
            )
        if value is None:
            prod["stock"].pop(vkey(size, color), None)
        else:
            prod["stock"][vkey(size, color)] = value
        write_db(products)
    await m.answer(f"✅ {prod['name']} ({size}, {color}): " + ("hisoblanmaydi" if value is None else f"{value} ta"))


@admin.message(Command("fillstock"))
async def fillstock_cmd(m: types.Message):
    args = (m.text or "").split()[1:]
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit() or int(args[1]) > 100000:
        return await m.answer("Ishlatilishi: /fillstock ID soni\nMasalan: /fillstock 3 5")
    n = int(args[1])
    async with db_lock:
        products = load_products()
        prod = find_product(products, int(args[0]))
        if not prod:
            return await m.answer("Bunday ID topilmadi. /list")
        for s in prod["sizes"] or ["Standart"]:
            for c in prod["colors"] or ["Standart"]:
                prod["stock"][vkey(s, c)] = n
        write_db(products)
    await m.answer(f"✅ {prod['name']}: hamma razmer va rangga {n} ta qo'yildi.")


@admin.message(Command("orders"))
async def orders_cmd(m: types.Message):
    orders = load_orders()[-10:][::-1]
    if not orders:
        return await m.answer("Buyurtmalar hali yo'q.")
    lines = [
        f"#{o['id']} {STATUS.get(o['status'], o['status'])} | {money(o['total'])} so'm | {o.get('name', '')} | {fmt_ts(o['ts'])}"
        for o in orders
    ]
    await send_long(m, "\n".join(lines) + "\n\nBatafsil: /order KOD")


@admin.message(Command("order"))
async def order_cmd(m: types.Message):
    args = (m.text or "").split()
    if len(args) != 2:
        return await m.answer("Ishlatilishi: /order A1B2C3")
    oid = args[1].lstrip("#").upper()
    o = next((x for x in load_orders() if x["id"] == oid), None)
    if not o:
        return await m.answer("Bunday buyurtma topilmadi.")
    await m.answer(order_text(o), reply_markup=order_kb(o))


@admin.message(Command("report"))
async def report_cmd(m: types.Message):
    args = (m.text or "").split()
    days = 1
    if len(args) > 1 and args[1].isdigit():
        days = min(max(int(args[1]), 1), 90)
    await m.answer(build_report(load_orders(), load_sales(), days))


@admin.message(Command("sales"))
async def sales_cmd(m: types.Message):
    start = int(datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    today = [s for s in load_sales() if s["ts"] >= start][-30:]
    if not today:
        return await m.answer("Bugun do'konda savdo yozilmagan.")
    lines = [
        f"{fmt_ts(s['ts'])} | {s['name']} ({s['size']}, {s['color']}) x{s['qty']} | {s.get('by_name', '')}"
        for s in today
    ]
    await send_long(m, "\n".join(lines))


@admin.message(Command("backup"))
async def backup_cmd(m: types.Message):
    sent = 0
    for path, name in ((DB, "products.json"), (ORDERS_DB, "orders.json"), (SALES_DB, "sales.json")):
        if os.path.exists(path):
            with open(path, "rb") as f:
                await m.answer_document(BufferedInputFile(f.read(), filename=name))
            sent += 1
    if not sent:
        await m.answer("Hali saqlangan fayl yo'q.")


@admin.callback_query(F.data.startswith("o:"))
async def order_action(cb: types.CallbackQuery):
    try:
        _, oid, action = cb.data.split(":")
    except ValueError:
        return await cb.answer()
    async with db_lock:
        orders = load_orders()
        o = next((x for x in orders if x["id"] == oid), None)
        if not o:
            return await cb.answer("Buyurtma topilmadi", show_alert=True)
        cur = o["status"]
        allowed = (NEXT.get(cur, (None,))[0] == action) or (
            action == "cancelled" and cur in ("new", "confirmed", "shipping")
        )
        if not allowed:
            await cb.answer("Bu buyurtma holati allaqachon o'zgargan", show_alert=True)
            if cb.message:
                with suppress(Exception):
                    await cb.message.edit_text(order_text(o), reply_markup=order_kb(o))
            return
        if action == "cancelled":
            products = load_products()
            restore_stock(products, o["items"])
            write_db(products)
        o["status"] = action
        o["updated"] = int(time.time())
        write_json(ORDERS_DB, orders)
    if cb.message:
        with suppress(Exception):
            await cb.message.edit_text(order_text(o), reply_markup=order_kb(o))
    if o.get("user_id") and action in CUSTOMER_MSG:
        with suppress(Exception):
            await bot.send_message(o["user_id"], CUSTOMER_MSG[action].format(id=o["id"]))
    await cb.answer("Yangilandi")


@admin.message(F.document)
async def restore(m: types.Message):
    name = m.document.file_name
    if name not in ("products.json", "orders.json", "sales.json"):
        return
    try:
        buf = io.BytesIO()
        await bot.download(m.document, destination=buf)
        data = json.loads(buf.getvalue().decode("utf-8"))
        async with db_lock:
            if name == "products.json":
                items = clean_products(data)
                write_db(items)
                count = len(items)
            else:
                if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
                    raise ValueError("noto'g'ri tuzilma")
                write_json(ORDERS_DB if name == "orders.json" else SALES_DB, data)
                count = len(data)
        if name == "products.json":
            with suppress(Exception):
                await pin_only(m.message_id)  # kelajakda avtomatik tiklanishi uchun qadaymiz
        await m.answer(f"♻️ {name} tiklandi: {count} ta yozuv.")
    except Exception:
        logging.exception("Tiklashda xatolik")
        await m.answer("Fayl noto'g'ri.")


# Eng oxirida: rasm kutilayotganda boshqa narsa yuborilsa
@admin.message(Add.photo)
async def add_photo_wrong(m: types.Message):
    await m.answer("Iltimos, rasm yuboring (fayl emas, oddiy foto). Bekor qilish: /cancel")


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
    if message.from_user:
        if message.from_user.id == ADMIN_ID:
            await message.answer("Siz adminsiz. Buyruqlar ro'yxati: /help")
        elif message.from_user.id in SELLER_IDS:
            await message.answer("Siz xodimsiz. Buyruqlar ro'yxati: /help")


# ====================== XAVFSIZLIK ======================
def verify_init_data(init_data: str):
    """Telegram WebApp initData imzosini tekshiradi. To'g'ri bo'lsa user dict qaytaradi."""
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received = pairs.pop("hash", None)
        if not received:
            return None
        check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, received):
            return None
        if time.time() - int(pairs.get("auth_date", "0")) > 86400:
            return None
        user = json.loads(pairs.get("user", "{}"))
        return user if isinstance(user, dict) and user.get("id") else None
    except Exception:
        return None


RATE = {}


def too_many(ip, limit=5, window=60):
    now = time.time()
    hits = [t for t in RATE.get(ip, []) if now - t < window]
    if len(hits) >= limit:
        RATE[ip] = hits
        return True
    hits.append(now)
    RATE[ip] = hits
    if len(RATE) > 5000:
        RATE.clear()
    return False


def client_ip(request: Request):
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "-"


# ====================== SERVER ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(DB):
        await restore_from_pinned()
    await bot.set_webhook(
        f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=False,
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
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(token, WEBHOOK_SECRET):
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
    return JSONResponse([public_product(p) for p in load_products()], headers={"Cache-Control": "no-store"})


IMG_CACHE: "OrderedDict[str, bytes]" = OrderedDict()
IMG_CACHE_MAX = 100


@app.get("/api/img/{file_id}")
async def api_img(file_id: str):
    # Faqat bazadagi tovarlarning rasmlari beriladi
    if not any(str(p.get("img", "")).endswith("/" + file_id) for p in load_products()):
        return Response(status_code=404)
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


def err(message, status=400):
    return JSONResponse({"status": "error", "message": message}, status_code=status)


async def rollback_order(order_id):
    """Adminga xabar yuborilmasa, buyurtmani o'chirib, qoldiqni qaytaradi."""
    async with db_lock:
        orders = load_orders()
        o = next((x for x in orders if x["id"] == order_id), None)
        if not o:
            return
        products = load_products()
        restore_stock(products, o["items"])
        write_db(products)
        write_json(ORDERS_DB, [x for x in orders if x["id"] != order_id])


@app.post("/api/order")
async def create_order(request: Request):
    if too_many(client_ip(request)):
        return err("Juda ko'p so'rov. Birozdan keyin urinib ko'ring.", 429)

    try:
        data = await request.json()
    except Exception:
        return err("Noto'g'ri so'rov")
    if not isinstance(data, dict):
        return err("Noto'g'ri so'rov")

    cart = data.get("cart")
    if not isinstance(cart, list) or not cart:
        return err("Savat bo'sh")

    # Mijoz Telegram orqali kelganini imzo bilan tekshiramiz
    verified = verify_init_data(str(data.get("init_data") or ""))
    if STRICT_ORDERS and not verified:
        return err("Do'konni Telegram ichidan oching", 403)

    name = str(data.get("name") or "").strip()[:60]
    phone = re.sub(r"[^\d+\-\s()]", "", str(data.get("phone") or "")).strip()[:20]
    address = str(data.get("address") or "").strip()[:200]

    async with db_lock:
        products = load_products()
        byid = {p["id"]: p for p in products}
        wanted = {}
        items = []
        for item in cart[:50]:
            if not isinstance(item, dict):
                continue
            prod = byid.get(to_int(item.get("id"), -1))
            if not prod:
                return err("Mahsulot topilmadi. Sahifa yangilanadi.", 409)
            size = str(item.get("size") or "").strip()[:30]
            color = str(item.get("color") or "").strip()[:30]
            if size not in (prod["sizes"] or ["Standart"]) or color not in (prod["colors"] or ["Standart"]):
                return err("Tovar ma'lumoti o'zgargan. Sahifa yangilanadi.", 409)
            qty = min(max(to_int(item.get("qty") or item.get("quantity"), 1), 1), 99)
            key = (prod["id"], size, color)
            wanted[key] = wanted.get(key, 0) + qty
            items.append({
                "pid": prod["id"], "name": prod["name"], "size": size, "color": color,
                "qty": qty, "price": prod["price"],  # narx faqat serverdan
            })
        if not items:
            return err("Savat bo'sh")

        problem = reserve(byid, wanted)
        if problem:
            return err(problem, 409)
        write_db(products)

        orders = load_orders()
        taken = {o["id"] for o in orders}
        order_id = secrets.token_hex(3).upper()
        while order_id in taken:
            order_id = secrets.token_hex(3).upper()
        order = {
            "id": order_id,
            "ts": int(time.time()),
            "status": "new",
            "items": items,
            "total": sum(i["price"] * i["qty"] for i in items),
            "name": name,
            "phone": phone,
            "address": address,
            "verified": bool(verified),
            "user_id": verified["id"] if verified else None,
            "tg_name": verified.get("first_name", "") if verified else "",
            "tg_username": verified.get("username", "") if verified else "",
        }
        orders.append(order)
        write_json(ORDERS_DB, orders)

        low = []
        for (pid, size, color) in wanted:
            left = get_stock(byid[pid], size, color)
            if left is not None and left <= LOW_STOCK:
                low.append((byid[pid]["name"], size, color, left))

    logging.info(order_text(order))

    try:
        await bot.send_message(ADMIN_ID, order_text(order), reply_markup=order_kb(order))
    except Exception:
        logging.exception("Adminga xabar yuborib bo'lmadi")
        await rollback_order(order_id)
        return err("Xatolik, qayta urinib ko'ring", 500)

    if low:
        with suppress(Exception):
            await bot.send_message(ADMIN_ID, low_text(low))

    # Tasdiq faqat imzosi tekshirilgan mijozga yuboriladi
    if verified:
        with suppress(Exception):
            await bot.send_message(
                verified["id"],
                f"✅ Buyurtmangiz #{order_id} qabul qilindi.\n"
                f"Jami: {money(order['total'])} so'm. Tez orada siz bilan bog'lanamiz.",
            )

    return {"status": "success", "message": "Buyurtma qabul qilindi!", "order_id": order_id}
