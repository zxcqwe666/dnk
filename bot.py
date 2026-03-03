import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    WebAppData,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from db import (
    fetch_last_orders, 
    init_db, 
    save_order, 
    save_user_profile,
    update_order_status,
    get_order_status_history,
    fetch_orders_by_status,
    fetch_user_orders
)


load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")  # URL мини-приложения

if not API_TOKEN:
    raise RuntimeError("Please set BOT_TOKEN in your .env file")


logging.basicConfig(level=logging.INFO)


@dataclass
class Product:
    id: str
    name: str
    price: int  # in RUB
    description: str


CATALOG: Dict[str, List[Product]] = {
    "sneakers": [
        Product(
            id="snk1",
            name="Nike Air Max 270",
            price=15990,
            description="Оригинальные Nike Air Max 270. Размеры 36-45.",
        ),
        Product(
            id="snk2",
            name="Adidas Yeezy Boost 350",
            price=24990,
            description="Adidas Yeezy Boost 350 V2. Лимитированная коллекция.",
        ),
    ],
    "clothes": [
        Product(
            id="cl1",
            name="Худи Essentials",
            price=7990,
            description="Уютное худи oversize. Размеры XS-XL.",
        ),
        Product(
            id="cl2",
            name="Футболка Basic",
            price=2990,
            description="Базовая хлопковая футболка, много цветов.",
        ),
    ],
}


CATEGORY_TITLES = {
    "sneakers": "Кроссовки",
    "clothes": "Одежда",
}


class OrderStates(StatesGroup):
    choosing_category = State()
    choosing_product = State()
    confirming_order = State()


def format_price(amount: int) -> str:
    return f"{amount:,} ₽".replace(",", " ")


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if WEBAPP_URL:
        kb.button(
            text="Открыть магазин",
            web_app=WebAppInfo(url=WEBAPP_URL),
        )
    else:
        kb.button(text="Mini App недоступен", callback_data="menu:noop")
    kb.adjust(1)
    return kb.as_markup()


def categories_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for cid, title in CATEGORY_TITLES.items():
        kb.button(text=title, callback_data=f"cat:{cid}")
    kb.button(text="⬅️ Назад", callback_data="back:main")
    kb.adjust(1)
    return kb.as_markup()


def products_kb(category_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in CATALOG.get(category_id, []):
        kb.button(
            text=f"{p.name} — {format_price(p.price)}",
            callback_data=f"prod:{p.id}",
        )
    kb.button(text="⬅️ Назад к категориям", callback_data="back:categories")
    kb.adjust(1)
    return kb.as_markup()


def product_actions_kb(product_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить в корзину 🛒", callback_data=f"cart:add:{product_id}")
    kb.button(text="⬅️ Назад к товарам", callback_data="back:products")
    kb.adjust(1)
    return kb.as_markup()


def cart_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Оформить заказ ✅", callback_data="cart:checkout")
    kb.button(text="Очистить корзину 🗑", callback_data="cart:clear")
    kb.button(text="⬅️ В главное меню", callback_data="back:main")
    kb.adjust(1)
    return kb.as_markup()


def find_product_by_id(pid: str) -> Product | None:
    for products in CATALOG.values():
        for p in products:
            if p.id == pid:
                return p
    return None


def get_cart(storage: Dict, user_id: int) -> Dict[str, int]:
    return storage.setdefault(user_id, {})


async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.text and message.text.startswith("/start "):
        payload = message.text.split(maxsplit=1)[1].strip()
        if payload == "myorders":
            await cmd_myorders(message)
            return
    text = (
        "Привет! 👋\n\n"
        "Я бот-магазин оригинальных кроссовок и одежды.\n"
        "Чтобы оформить заказ, открой мини‑приложение:"
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def cmd_catalog(message: Message, state: FSMContext) -> None:
    await state.set_state(OrderStates.choosing_category)
    await message.answer("Выберите категорию товара:", reply_markup=categories_kb())


async def on_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Главное меню. Выберите раздел:", reply_markup=main_menu_kb()
    )
    await callback.answer()


async def on_menu(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":", maxsplit=1)[1]
    if action == "catalog":
        await state.set_state(OrderStates.choosing_category)
        await callback.message.edit_text(
            "Выберите категорию товара:", reply_markup=categories_kb()
        )
    elif action == "cart":
        await show_cart(callback)
    elif action == "help":
        await callback.message.edit_text(
            "Если у вас есть вопросы по размерам, наличию или оплате — "
            "напишите нашему менеджеру: @your_manager_username\n\n"
            "Или просто продолжайте выбирать товары в каталоге.",
            reply_markup=main_menu_kb(),
        )
    await callback.answer()


async def on_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(category_id=category_id)
    await state.set_state(OrderStates.choosing_product)
    title = CATEGORY_TITLES.get(category_id, "Категория")
    await callback.message.edit_text(
        f"{title}\n\nВыберите модель:", reply_markup=products_kb(category_id)
    )
    await callback.answer()


async def on_back(callback: CallbackQuery, state: FSMContext) -> None:
    _, where = callback.data.split(":", maxsplit=1)
    data = await state.get_data()

    if where == "main":
        await on_main_menu(callback, state)
    elif where == "categories":
        await state.set_state(OrderStates.choosing_category)
        await callback.message.edit_text(
            "Выберите категорию товара:", reply_markup=categories_kb()
        )
        await callback.answer()
    elif where == "products":
        category_id = data.get("category_id", "sneakers")
        await state.set_state(OrderStates.choosing_product)
        await callback.message.edit_text(
            "Выберите модель:", reply_markup=products_kb(category_id)
        )
        await callback.answer()


async def on_product(callback: CallbackQuery, state: FSMContext) -> None:
    pid = callback.data.split(":", maxsplit=1)[1]
    product = find_product_by_id(pid)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    await state.update_data(product_id=pid)
    text = (
        f"<b>{product.name}</b>\n"
        f"{product.description}\n\n"
        f"<b>Цена:</b> {format_price(product.price)}"
    )
    await callback.message.edit_text(text, reply_markup=product_actions_kb(pid))
    await callback.answer()


CART_STORAGE: Dict[int, Dict[str, int]] = {}


async def show_cart(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    cart = get_cart(CART_STORAGE, user_id)

    if not cart:
        await callback.message.edit_text(
            "Ваша корзина пуста. Перейдите в каталог и добавьте товары.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    lines = ["<b>Ваша корзина:</b>\n"]
    total = 0
    for pid, qty in cart.items():
        product = find_product_by_id(pid)
        if not product:
            continue
        line_total = product.price * qty
        total += line_total
        lines.append(
            f"{product.name} — {qty} шт. × {format_price(product.price)} "
            f"= {format_price(line_total)}"
        )
    lines.append(f"\n<b>Итого:</b> {format_price(total)}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=cart_kb(),
    )
    await callback.answer()


async def on_cart_actions(callback: CallbackQuery) -> None:
    parts = callback.data.split(":", maxsplit=2)
    action = parts[1]
    user_id = callback.from_user.id
    cart = get_cart(CART_STORAGE, user_id)

    if action == "add":
        pid = parts[2]
        product = find_product_by_id(pid)
        if not product:
            await callback.answer("Товар не найден", show_alert=True)
            return
        cart[pid] = cart.get(pid, 0) + 1
        await callback.answer("Добавлено в корзину ✅", show_alert=False)
    elif action == "clear":
        cart.clear()
        await callback.message.edit_text(
            "Корзина очищена.", reply_markup=main_menu_kb()
        )
        await callback.answer()
    elif action == "checkout":
        if not cart:
            await callback.answer("Корзина пуста", show_alert=True)
            return

        lines = ["<b>Заказ оформлен (черновик):</b>\n"]
        total = 0
        for pid, qty in cart.items():
            product = find_product_by_id(pid)
            if not product:
                continue
            line_total = product.price * qty
            total += line_total
            lines.append(
                f"{product.name} — {qty} шт. × {format_price(product.price)} "
                f"= {format_price(line_total)}"
            )
        lines.append(f"\n<b>Итого к оплате:</b> {format_price(total)}\n")
        lines.append(
            "Для завершения заказа напишите, пожалуйста, менеджеру: "
            "@your_manager_username, указав номер телефона и адрес доставки."
        )

        cart.clear()
        await callback.message.edit_text(
            "\n".join(lines), reply_markup=main_menu_kb()
        )
        await callback.answer()


async def cmd_help(message: Message) -> None:
    await message.answer(
        "Я бот-магазин обуви и одежды.\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/help — помощь\n"
        "/myorders — мои заказы\n"
        "/orders — последние заказы (только для админа)\n"
        "/order &lt;id&gt; — детали заказа (только для админа)\n\n"
        "Для вопросов по оплате и доставке напишите менеджеру: "
        "@your_manager_username"
    )


async def on_unknown_message(message: Message) -> None:
    # Записываем все сообщения для отладки
    with open("all_messages.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== UNKNOWN {datetime.now().isoformat()} ===\n")
        f.write(f"Content type: {message.content_type}\n")
        f.write(f"Message: {message}\n")
    
    await message.answer(
        "Не понимаю это сообщение.\n"
        "Используйте кнопки или команду /start, чтобы вернуться в главное меню."
    )


async def debug_all_messages(message: Message) -> None:
    # Записываем все входящие сообщения для отладки
    with open("all_messages.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== DEBUG {datetime.now().isoformat()} ===\n")
        f.write(f"Content type: {message.content_type}\n")
        f.write(f"Message: {message}\n")
        if hasattr(message, 'web_app_data') and message.web_app_data:
            f.write(f"WebApp data: {message.web_app_data.data}\n")


async def on_webapp_data(message: Message) -> None:
    print(f"[DEBUG] on_webapp_data called, message type: {message.content_type}")  # Отладочный вывод
    print(f"[DEBUG] message: {message}")  # Отладочный вывод
    
    # Если это не WebApp данные, выходим
    if not hasattr(message, 'web_app_data') or not message.web_app_data:
        return
    
    try:
        payload: dict[str, Any] = json.loads(message.web_app_data.data)
        print(f"[DEBUG] web_app_data: {message.web_app_data}")  # Отладочный вывод
        print(f"[DEBUG] web_app_data.data: {message.web_app_data.data}")  # Отладочный вывод
    except Exception as e:
        print(f"[ERROR] Failed to parse web app data: {e}")  # Отладочный вывод
        await message.answer("Не удалось прочитать данные заказа.")
        return

    kind = payload.get("type")
    user = message.from_user
    
    print(f"[DEBUG] Received payload type: {kind}")
    print(f"[DEBUG] Payload content: {payload}")
    
    # Записываем в файл для отладки
    with open("debug.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== {datetime.now().isoformat()} ===\n")
        f.write(f"Type: {kind}\n")
        f.write(f"Payload: {payload}\n")
        f.write(f"User: {user.id} ({user.username})\n")

    if kind == "order":
        # Проверка структуры заказа
        if not isinstance(payload.get("items"), dict):
            await message.answer("❌ Некорректная структура заказа. Обновите страницу и попробуйте снова.")
            return
        
        items: dict[str, int] = payload.get("items", {})
        if not items:
            await message.answer("🛒 Заказ пустой. Добавьте товары в корзину и повторите.")
            return
        
        # Проверка товаров и расчет суммы
        calculated_total = 0
        invalid_items = []
        
        for product_id, qty in items.items():
            if not isinstance(qty, int) or qty <= 0:
                await message.answer(f"❌ Некорректное количество для товара {product_id}")
                return
            
            product = find_product_by_id(product_id)
            if not product:
                invalid_items.append(product_id)
                continue
            
            calculated_total += product.price * qty
        
        if invalid_items:
            await message.answer(f"❌ Некоторые товары недоступны: {', '.join(invalid_items)}")
            return
        
        # Проверка суммы
        order_total = int(payload.get("total", 0))
        if order_total <= 0:
            await message.answer("❌ Сумма заказа должна быть больше 0")
            return
        
        if order_total != calculated_total:
            await message.answer(f"❌ Ошибка расчета суммы. Ожидалось: {format_price(calculated_total)}, получено: {format_price(order_total)}")
            return
        
        # Проверка профиля (опционально, но рекомендуется)
        profile = payload.get("profile", {})
        missing_fields = []
        if not profile.get("city"):
            missing_fields.append("город")
        if not profile.get("phone"):
            missing_fields.append("телефон")
        
        warning = ""
        if missing_fields:
            warning = f"⚠️ Внимание: не заполнены {', '.join(missing_fields)}. "
        
        # Сохранение заказа
        order_id = await save_order(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            payload=payload,
        )

        total = int(payload.get("total", 0))
        await message.answer(
            f"✅ Заказ №{order_id} успешно оформлен!\n"
            f"💰 Сумма: {format_price(total)}\n"
            f"📦 Товаров: {sum(items.values())} шт.\n\n"
            "Менеджер скоро свяжется с вами для подтверждения."
        )
        return

    if kind == "profile":
        profile = payload.get("profile") or {}
        await save_user_profile(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            profile=profile,
        )
        await message.answer("Профиль обновлён ✅")
        return

    if kind == "myorders":
        orders = await fetch_user_orders(user_id=user.id, limit=10)
        if not orders:
            await message.answer("У вас пока нет заказов.")
            return

        lines: list[str] = ["📦 Ваши заказы:\n"]
        for o in orders:
            lines.append(
                f"#{o['id']} — {format_price(o['total'])} — {o['created_at'][:10]}"
            )
        lines.append("\nЧтобы посмотреть детали заказа, нажмите /order номер")
        await message.answer("\n".join(lines))
        return

    await message.answer("Получены неподдерживаемые данные.")


ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # опционально, Telegram ID админа


async def cmd_orders(message: Message) -> None:
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        await message.answer("Команда доступна только администратору.")
        return

    orders = await fetch_last_orders(limit=20)
    if not orders:
        await message.answer("Заказов пока нет.")
        return

    lines: list[str] = ["📦 Последние заказы:\n"]
    for o in orders:
        user = o.get("username") or o.get("full_name") or f"ID:{o['user_id']}"
        lines.append(
            f"#{o['id']} — {format_price(o['total'])} — {user} — {o['created_at'][:10]}"
        )

    await message.answer("\n".join(lines))


async def cmd_myorders(message: Message) -> None:
    orders = await fetch_user_orders(user_id=message.from_user.id, limit=10)
    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    lines: list[str] = ["Ваши последние заказы:\n"]
    for o in orders:
        lines.append(
            f"#{o['id']} — {format_price(o['total'])} — {o['created_at']}"
        )

    lines.append(
        "\nЧтобы посмотреть детали конкретного заказа, отправьте его номер администратору."
    )
    await message.answer("\n".join(lines))


async def cmd_order_detail(message: Message) -> None:
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        await message.answer("Команда доступна только администратору.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Используйте формат: /order 123")
        return

    order_id = int(parts[1].strip())
    order = await fetch_order_by_id(order_id)
    if not order:
        await message.answer(f"Заказ #{order_id} не найден.")
        return

    payload = json.loads(order["payload_json"])
    items: dict[str, int] = payload.get("items", {})
    profile = payload.get("profile") or {}

    lines: list[str] = [
        f"Заказ #{order['id']} от {order['created_at']}",
        f"Сумма: {format_price(order['total'])}",
        "",
        "Товары:",
    ]

    if not items:
        lines.append("  (нет позиций)")
    else:
        for pid, qty in items.items():
            product = find_product_by_id(pid)
            name = product.name if product else pid
            price = product.price if product else 0
            line_total = price * qty
            price_text = (
                f"{format_price(price)} × {qty} = {format_price(line_total)}"
                if product
                else f"{qty} шт."
            )
            lines.append(f"- {name}: {price_text}")

    if profile:
        lines.append("\nПрофиль клиента:")
        if profile.get("shoe_size"):
            lines.append(f"Размер обуви: {profile['shoe_size']}")
        if profile.get("clothing_size"):
            lines.append(f"Размер одежды: {profile['clothing_size']}")
        if profile.get("city"):
            lines.append(f"Город: {profile['city']}")
        if profile.get("delivery"):
            lines.append(f"Доставка: {profile['delivery']}")
        if profile.get("phone"):
            lines.append(f"Телефон: {profile['phone']}")

    await message.answer("\n".join(lines))


async def cmd_set_status(message: Message) -> None:
    """Установить статус заказа (только для админа)"""
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        await message.answer("Команда доступна только администратору.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Используйте формат: /setstatus <order_id> <status>\nСтатусы: new, processing, shipped, delivered, cancelled")
        return

    order_id = parts[1].strip()
    status = parts[2].strip()
    
    valid_statuses = ['new', 'processing', 'shipped', 'delivered', 'cancelled']
    if status not in valid_statuses:
        await message.answer(f"Неверный статус. Доступные: {', '.join(valid_statuses)}")
        return

    try:
        order_id = int(order_id)
        success = await update_order_status(order_id, status)
        if success:
            await message.answer(f"✅ Статус заказа #{order_id} изменен на '{status}'")
        else:
            await message.answer(f"❌ Заказ #{order_id} не найден")
    except ValueError:
        await message.answer("❌ Неверный формат ID заказа")


async def cmd_status_orders(message: Message) -> None:
    """Показать заказы по статусу (только для админа)"""
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        await message.answer("Команда доступна только администратору.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используйте формат: /status <status>\nСтатусы: new, processing, shipped, delivered, cancelled")
        return

    status = parts[1].strip()
    orders = await fetch_orders_by_status(status, limit=20)
    
    if not orders:
        await message.answer(f"Заказов со статусом '{status}' нет")
        return

    lines = [f"Заказы со статусом '{status}':\n"]
    for o in orders:
        user = o.get("username") or o.get("full_name") or o["user_id"]
        tracking = f" | 📦 {o['tracking_number']}" if o.get('tracking_number') else ""
        lines.append(f"#{o['id']} — {format_price(o['total'])} — {user}{tracking}")
    
    await message.answer("\n".join(lines))


async def cmd_order_history(message: Message) -> None:
    """Показать историю статусов заказа (только для админа)"""
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        await message.answer("Команда доступна только администратору.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используйте формат: /history <order_id>")
        return

    try:
        order_id = int(parts[1].strip())
        history = await get_order_status_history(order_id)
        
        if not history:
            await message.answer(f"История для заказа #{order_id} не найдена")
            return

        lines = [f"История статусов заказа #{order_id}:\n"]
        for h in history:
            old = f"из '{h['old_status']}'" if h['old_status'] else ""
            comment = f" | {h['comment']}" if h['comment'] else ""
            lines.append(f"{h['created_at']}: {old} → '{h['new_status']}'{comment}")
        
        await message.answer("\n".join(lines))
    except ValueError:
        await message.answer("❌ Неверный формат ID заказа")


async def main() -> None:
    bot = Bot(
        token=API_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    await init_db()
    dp = Dispatcher(storage=storage)

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(debug_all_messages)  # Логируем все сообщения

    dp.callback_query.register(on_main_menu, F.data == "back:main")
    dp.callback_query.register(on_back, F.data.startswith("back:"))
    dp.callback_query.register(on_menu, F.data.startswith("menu:"))
    dp.callback_query.register(on_category, F.data.startswith("cat:"))
    dp.callback_query.register(on_product, F.data.startswith("prod:"))
    dp.callback_query.register(on_cart_actions, F.data.startswith("cart:"))

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

