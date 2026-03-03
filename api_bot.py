#!/usr/bin/env python3
import sqlite3
import json
import requests
from datetime import datetime

# Настройки
BOT_TOKEN = "8754935228:AAHqTmrgSsFDtVwXmW-xuAqD3oaYs-_PLps"
API_BASE = "http://localhost:5001/api"

def get_orders_from_api(user_id):
    """Получение заказов через API"""
    try:
        response = requests.get(f"{API_BASE}/orders/{user_id}")
        if response.status_code == 200:
            return response.json().get('orders', [])
        return []
    except:
        return []

def send_telegram_message(chat_id, text):
    """Отправка сообщения через Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=data)
        return response.status_code == 200
    except:
        return False

def handle_start(chat_id, username):
    """Обработка команды /start"""
    text = """👋 <b>Добро пожаловать в DNK Store!</b>

🛍️ <b>Как оформить заказ:</b>
1. Откройте наш магазин
2. Выберите товары
3. Оформите заказ

📋 <b>Команды:</b>
/myorders - Мои заказы
/start - Главное меню

💡 <b>Заказы сохраняются автоматически!</b>"""
    
    return send_telegram_message(chat_id, text)

def handle_myorders(chat_id, user_id):
    """Обработка команды /myorders"""
    orders = get_orders_from_api(user_id)
    
    if not orders:
        text = "📦 <b>У вас пока нет заказов</b>\n\nОформите первый заказ в нашем магазине!"
        return send_telegram_message(chat_id, text)
    
    text = f"📦 <b>Ваши заказы ({len(orders)} шт.):</b>\n\n"
    
    for order in orders:
        items = order.get('items', {})
        total = order.get('total', 0)
        status = order.get('status', 'new')
        created = order.get('created_at', '')
        
        # Форматируем дату
        if created:
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created_str = dt.strftime('%d.%m.%Y %H:%M')
            except:
                created_str = created
        else:
            created_str = 'неизвестно'
        
        text += f"🔹 <b>Заказ #{order['id']}</b>\n"
        text += f"💰 <b>Сумма:</b> {total:,} ₽\n"
        text += f"📊 <b>Статус:</b> {status}\n"
        text += f"📅 <b>Дата:</b> {created_str}\n"
        text += f"🛍️ <b>Товаров:</b> {sum(items.values())} шт.\n\n"
    
    return send_telegram_message(chat_id, text)

def handle_message(chat_id, user_id, username, text):
    """Обработка входящих сообщений"""
    text = text.strip()
    
    if text == '/start':
        return handle_start(chat_id, username)
    elif text == '/myorders':
        return handle_myorders(chat_id, user_id)
    else:
        # Неизвестная команда
        help_text = """🤔 <b>Неизвестная команда</b>

Доступные команды:
/start - Главное меню
/myorders - Мои заказы"""
        
        return send_telegram_message(chat_id, help_text)

if __name__ == "__main__":
    print("🤖 API Bot готов к работе!")
    print("📡 Использует Telegram Bot API напрямую")
    print("🔗 Работает с API сервером на localhost:5000")
    print("\n📝 Для тестирования:")
    print("1. Запустите API сервер: python3 api_server.py")
    print("2. Отправьте /start или /myorders в Telegram")
    
    # Здесь можно добавить webhook или polling, но для тестирования пока так
