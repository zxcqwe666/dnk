// API функции для отправки заказов
const API_BASE = 'http://localhost:5001/api';

// Отправка заказа на API сервер
async function sendOrderToAPI(orderData) {
    try {
        const response = await fetch(`${API_BASE}/order`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: orderData.user_id || 957766610,
                username: orderData.username || 'emoslutt6666',
                order_data: orderData
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('✅ Заказ отправлен на API:', result);
            alert(`✅ ${result.message}`);
            return true;
        } else {
            console.error('❌ Ошибка API:', result);
            alert(`❌ Ошибка: ${result.error}`);
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка соединения с API:', error);
        alert('❌ Не удалось соединиться с сервером. Попробуйте позже.');
        return false;
    }
}

// Получение заказов пользователя
async function getUserOrders(userId) {
    try {
        const response = await fetch(`${API_BASE}/orders/${userId}`);
        const result = await response.json();
        
        if (response.ok) {
            console.log('📦 Заказы получены:', result.orders);
            return result.orders;
        } else {
            console.error('❌ Ошибка получения заказов:', result);
            return [];
        }
    } catch (error) {
        console.error('❌ Ошибка соединения с API:', error);
        return [];
    }
}

// Проверка работы API
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const result = await response.json();
        
        if (response.ok) {
            console.log('🟢 API работает:', result);
            return true;
        } else {
            console.log('🔴 API не отвечает');
            return false;
        }
    } catch (error) {
        console.log('🔴 API недоступен:', error);
        return false;
    }
}

// Обновлённая функция отправки заказа
function sendWebAppData(payload) {
    const tg = window.Telegram.WebApp;
    
    if (!tg) {
        alert("❌ Ошибка: Telegram WebApp не найден");
        return false;
    }
    
    // Сначала пробуем отправить на API
    console.log('📤 Отправка заказа на API...');
    
    sendOrderToAPI(payload).then(success => {
        if (success) {
            // Если успешно отправлено на API, закрываем WebApp
            tg.close();
        } else {
            // Если API не сработало, пробуем старый способ
            console.log('🔄 Пробуем отправить через Telegram...');
            try {
                tg.sendData(JSON.stringify(payload));
                alert("✅ Заказ отправлен!");
                tg.close();
            } catch (e) {
                alert(`❌ Ошибка отправки: ${e.message}`);
            }
        }
    });
    
    return true;
}

// Проверка API при загрузке
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 Проверка API сервера...');
    checkAPIHealth().then(isWorking => {
        if (isWorking) {
            console.log('✅ API сервер доступен');
        } else {
            console.log('⚠️ API сервер недоступен, будет использован Telegram');
        }
    });
});

// Экспорт функций для использования в основном коде
window.API = {
    sendOrder: sendOrderToAPI,
    getOrders: getUserOrders,
    checkHealth: checkAPIHealth
};
