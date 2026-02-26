import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


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
    kb.button(text="Каталог 👟", callback_data="menu:catalog")
    kb.button(text="Корзина 🛒", callback_data="menu:cart")
    kb.button(text="Помощь ❓", callback_data="menu:help")
    if WEBAPP_URL:
        kb.button(
            text="Открыть Mini App 🦄",
            web_app=WebAppInfo(url=WEBAPP_URL),
        )
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
    text = (
        "Привет! 👋\n\n"
        "Я бот-магазин оригинальных кроссовок и одежды.\n"
        "Здесь вы можете заказать топовые модели по лучшим ценам.\n\n"
        "Выберите раздел:"
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
        "/catalog — открыть каталог\n"
        "/help — помощь\n\n"
        "Для вопросов по оплате и доставке напишите менеджеру: "
        "@your_manager_username"
    )


async def on_unknown_message(message: Message) -> None:
    await message.answer(
        "Не понимаю это сообщение.\n"
        "Используйте кнопки или команду /start, чтобы вернуться в главное меню."
    )


async def main() -> None:
    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_catalog, Command("catalog"))
    dp.message.register(on_unknown_message)

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

