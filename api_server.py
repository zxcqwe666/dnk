#!/usr/bin/env python3
from flask import Flask, request, jsonify
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)

DB_PATH = "/Users/ilasudilovskij/tgbot/dnk.sqlite3"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            order_data TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_order(user_id, username, order_data):
    """Сохранение заказа"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO api_orders (user_id, username, order_data)
        VALUES (?, ?, ?)
    ''', (user_id, username, json.dumps(order_data)))
    
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return order_id

def get_orders(user_id):
    """Получение заказов пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, order_data, status, created_at FROM api_orders 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,))
    
    orders = cursor.fetchall()
    conn.close()
    
    return orders

@app.route('/api/order', methods=['POST'])
def create_order():
    """Принимаем заказы от WebApp"""
    try:
        data = request.get_json()
        
        # Валидация
        if not data or 'user_id' not in data or 'order_data' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        user_id = data['user_id']
        username = data.get('username', 'unknown')
        order_data = data['order_data']
        
        # Сохранение
        order_id = save_order(user_id, username, order_data)
        
        # Логирование
        with open('api_orders.log', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - Order #{order_id} from user {username}\n")
            f.write(f"Data: {json.dumps(order_data)}\n\n")
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': f'Заказ #{order_id} успешно оформлен!'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:user_id>', methods=['GET'])
def list_orders(user_id):
    """Получение заказов пользователя"""
    try:
        orders = get_orders(user_id)
        
        result = []
        for order in orders:
            order_data = json.loads(order[1])
            result.append({
                'id': order[0],
                'status': order[2],
                'created_at': order[3],
                'items': order_data.get('items', {}),
                'total': order_data.get('total', 0),
                'profile': order_data.get('profile', {})
            })
        
        return jsonify({'orders': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работы API"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    init_db()
    print("🚀 API сервер запущен на http://localhost:5001")
    print("📦 Эндпоинты:")
    print("  POST /api/order - создание заказа")
    print("  GET  /api/orders/<user_id> - получение заказов")
    print("  GET  /api/health - проверка работы")
    app.run(debug=True, host='0.0.0.0', port=5001)
