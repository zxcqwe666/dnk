#!/usr/bin/env python3
from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# Временное хранилище заказов в памяти
orders_storage = []

@app.route('/')
def home():
    return "DNK API Server работает!"

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok', 
        'timestamp': datetime.now().isoformat(),
        'orders_count': len(orders_storage)
    })

@app.route('/api/order', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        
        if not data or 'order_data' not in data:
            return jsonify({'error': 'Missing order_data'}), 400
        
        # Создаём заказ
        order = {
            'id': len(orders_storage) + 1,
            'user_id': data.get('user_id', 0),
            'username': data.get('username', 'unknown'),
            'order_data': data['order_data'],
            'status': 'new',
            'created_at': datetime.now().isoformat()
        }
        
        orders_storage.append(order)
        
        # Логирование
        with open('orders.log', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - Order #{order['id']} from {order['username']}\n")
            f.write(f"Data: {json.dumps(data)}\n\n")
        
        print(f"✅ Заказ #{order['id']} сохранён!")
        
        return jsonify({
            'success': True,
            'order_id': order['id'],
            'message': f'Заказ #{order["id"]} успешно оформлен!'
        })
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:user_id>')
def get_orders(user_id):
    try:
        user_orders = [o for o in orders_storage if o['user_id'] == user_id]
        
        result = []
        for order in user_orders:
            order_data = order['order_data']
            result.append({
                'id': order['id'],
                'status': order['status'],
                'created_at': order['created_at'],
                'items': order_data.get('items', {}),
                'total': order_data.get('total', 0),
                'profile': order_data.get('profile', {})
            })
        
        print(f"📦 Найдено {len(result)} заказов для пользователя {user_id}")
        
        return jsonify({'orders': result})
        
    except Exception as e:
        print(f"❌ Ошибка получения заказов: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Простой DNK API сервер на http://localhost:5001")
    print("📦 Эндпоинты:")
    print("  POST /api/order - создание заказа")
    print("  GET  /api/orders/<user_id> - получение заказов")
    print("  GET  /api/health - проверка работы")
    app.run(port=5001, debug=False)
