#!/usr/bin/env python3
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/')
def home():
    return "API работает!"

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("🚀 Тестовый API на http://localhost:5001")
    app.run(port=5001, debug=False)
