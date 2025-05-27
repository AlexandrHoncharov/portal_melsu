#!/usr/bin/env python3
"""
Тестовое приложение для демонстрации OAuth2 авторизации
через систему университета
"""

from flask import Flask, request, redirect, session, jsonify, render_template_string
import requests
import urllib.parse
import secrets

app = Flask(__name__)
app.secret_key = 'test-oauth-client-secret'

# Настройки OAuth2 (автоматически сгенерировано)
OAUTH_CONFIG = {
    'client_id': '5QxjGSt1HnPjrxZ5df84DEJM',
    'client_secret': 'FzUWEpS5WAq2JCaLGjqj0rVKX6ABdCy4sNnaR9TehRI0e8bx',
    'authorization_base_url': 'http://localhost:5000/oauth/authorize',
    'token_url': 'http://localhost:5000/oauth/token',
    'user_info_url': 'http://localhost:5000/api/oauth/user',
    'redirect_uri': 'http://localhost:3000/callback',
    'scope': 'read:profile read:email read:roles'
}


@app.route('/')
def index():
    """Главная страница тестового приложения"""
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Тестовое приложение университета</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container { 
                background: rgba(255,255,255,0.1); 
                padding: 40px; 
                border-radius: 15px; 
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            }
            .btn { 
                background: #820000; 
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px;
                text-decoration: none;
                display: inline-block;
                margin: 10px 5px;
                transition: all 0.3s;
            }
            .btn:hover { 
                background: #a00000; 
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .user-info { 
                background: rgba(255,255,255,0.2); 
                padding: 20px; 
                border-radius: 8px; 
                margin: 20px 0;
            }
            h1 { text-align: center; margin-bottom: 30px; }
            pre { 
                background: rgba(0,0,0,0.3); 
                padding: 15px; 
                border-radius: 8px; 
                overflow-x: auto;
                white-space: pre-wrap;
            }
            .status { font-weight: bold; color: #4CAF50; }
            .logout { background: #666; }
            .logout:hover { background: #888; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏛️ Тестовое приложение университета</h1>
            <p>Это демонстрационное приложение показывает, как другие сервисы университета могут авторизовать пользователей через центральную систему.</p>

            {% if session.get('user_info') %}
                <div class="user-info">
                    <h3>✅ Вы авторизованы!</h3>
                    <p><strong>Данные полученные от сервера авторизации:</strong></p>
                    <pre>{{ session['user_info'] | tojson(indent=2) }}</pre>

                    <a href="/profile" class="btn">👤 Получить полную информацию</a>
                    <a href="/logout" class="btn logout">🚪 Выйти</a>
                </div>
            {% else %}
                <div class="user-info">
                    <h3>🔐 Требуется авторизация</h3>
                    <p>Для доступа к приложению необходимо войти через систему университета.</p>

                    <a href="/login" class="btn">🔑 Войти через систему университета</a>
                </div>

                <div style="margin-top: 30px;">
                    <h4>ℹ️ Как это работает:</h4>
                    <ol>
                        <li>Нажмите "Войти через систему университета"</li>
                        <li>Вас перенаправит на страницу авторизации университета</li>
                        <li>Введите свои учетные данные</li>
                        <li>Подтвердите доступ к вашим данным</li>
                        <li>Вернитесь в это приложение уже авторизованным</li>
                    </ol>
                </div>
            {% endif %}

            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                <h4>🔧 Техническая информация:</h4>
                <p><strong>Client ID:</strong> {{ config.client_id }}</p>
                <p><strong>Requested Scopes:</strong> {{ config.scope }}</p>
                <p><strong>OAuth Server:</strong> {{ config.authorization_base_url }}</p>
            </div>
        </div>
    </body>
    </html>
    '''

    return render_template_string(template, session=session, config=OAUTH_CONFIG)


@app.route('/login')
def login():
    """Начало OAuth2 авторизации"""
    # Генерируем state для защиты от CSRF
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    # Формируем URL авторизации
    params = {
        'response_type': 'code',
        'client_id': OAUTH_CONFIG['client_id'],
        'redirect_uri': OAUTH_CONFIG['redirect_uri'],
        'scope': OAUTH_CONFIG['scope'],
        'state': state
    }

    auth_url = f"{OAUTH_CONFIG['authorization_base_url']}?{urllib.parse.urlencode(params)}"

    print(f"🔄 Перенаправляем на авторизацию: {auth_url}")
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """Обработка callback после авторизации"""
    # Проверяем state для защиты от CSRF
    if request.args.get('state') != session.get('oauth_state'):
        return jsonify({'error': 'Invalid state parameter'}), 400

    # Проверяем на ошибки
    if request.args.get('error'):
        return jsonify({'error': request.args.get('error')}), 400

    # Получаем authorization code
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'No authorization code received'}), 400

    print(f"📨 Получен authorization code: {code[:10]}...")

    # Обмениваем код на токен
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': OAUTH_CONFIG['redirect_uri'],
        'client_id': OAUTH_CONFIG['client_id'],
        'client_secret': OAUTH_CONFIG['client_secret']
    }

    try:
        token_response = requests.post(OAUTH_CONFIG['token_url'], data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()

        print(f"🎫 Получен access token: {tokens['access_token'][:10]}...")

        # Сохраняем токен в сессии
        session['access_token'] = tokens['access_token']

        # Получаем информацию о пользователе
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        user_response = requests.get(OAUTH_CONFIG['user_info_url'], headers=headers)
        user_response.raise_for_status()
        user_info = user_response.json()

        print(f"👤 Получена информация о пользователе: {user_info.get('username', 'Unknown')}")

        # Сохраняем информацию о пользователе
        session['user_info'] = user_info

        return redirect('/')

    except requests.RequestException as e:
        print(f"❌ Ошибка получения токена: {e}")
        return jsonify({'error': 'Failed to get access token'}), 500


@app.route('/profile')
def profile():
    """Страница с детальной информацией о пользователе"""
    if 'access_token' not in session:
        return redirect('/')

    try:
        # Получаем свежую информацию о пользователе
        headers = {'Authorization': f"Bearer {session['access_token']}"}
        response = requests.get(OAUTH_CONFIG['user_info_url'], headers=headers)
        response.raise_for_status()
        user_info = response.json()

        template = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Профиль пользователя</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 800px; 
                    margin: 50px auto; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                }
                .container { 
                    background: rgba(255,255,255,0.1); 
                    padding: 40px; 
                    border-radius: 15px; 
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                }
                .btn { 
                    background: #820000; 
                    color: white; 
                    padding: 12px 20px; 
                    border: none; 
                    border-radius: 8px; 
                    cursor: pointer; 
                    text-decoration: none;
                    display: inline-block;
                    margin: 5px;
                }
                .info-block { 
                    background: rgba(255,255,255,0.2); 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 15px 0;
                }
                pre { 
                    background: rgba(0,0,0,0.3); 
                    padding: 15px; 
                    border-radius: 8px; 
                    overflow-x: auto;
                    white-space: pre-wrap;
                }
                h1 { text-align: center; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>👤 Профиль пользователя</h1>

                <div class="info-block">
                    <h3>Основная информация:</h3>
                    <p><strong>ID:</strong> {{ user_info.get('id') }}</p>
                    <p><strong>Username:</strong> {{ user_info.get('username') }}</p>
                    {% if user_info.get('email') %}
                        <p><strong>Email:</strong> {{ user_info.get('email') }}</p>
                    {% endif %}
                    {% if user_info.get('full_name') %}
                        <p><strong>Полное имя:</strong> {{ user_info.get('full_name') }}</p>
                    {% endif %}
                </div>

                {% if user_info.get('roles') %}
                <div class="info-block">
                    <h3>Роли в системе:</h3>
                    <ul>
                        {% for role in user_info.get('display_roles', user_info.get('roles', [])) %}
                            <li>{{ role }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}

                {% if user_info.get('profile') %}
                <div class="info-block">
                    <h3>Детали профиля:</h3>
                    {% set profile = user_info.get('profile') %}
                    {% if profile.get('first_name') %}
                        <p><strong>Имя:</strong> {{ profile.get('first_name') }}</p>
                    {% endif %}
                    {% if profile.get('last_name') %}
                        <p><strong>Фамилия:</strong> {{ profile.get('last_name') }}</p>
                    {% endif %}
                    {% if profile.get('middle_name') %}
                        <p><strong>Отчество:</strong> {{ profile.get('middle_name') }}</p>
                    {% endif %}
                </div>
                {% endif %}

                <div class="info-block">
                    <h3>Полный ответ API:</h3>
                    <pre>{{ user_info | tojson(indent=2) }}</pre>
                </div>

                <a href="/" class="btn">🏠 На главную</a>
                <a href="/logout" class="btn" style="background: #666;">🚪 Выйти</a>
            </div>
        </body>
        </html>
        '''

        return render_template_string(template, user_info=user_info)

    except requests.RequestException as e:
        print(f"❌ Ошибка получения профиля: {e}")
        return jsonify({'error': 'Failed to get user profile'}), 500


@app.route('/logout')
def logout():
    """Выход из приложения"""
    session.clear()
    return redirect('/')


@app.route('/test-token')
def test_token():
    """Тестирование валидности токена"""
    if 'access_token' not in session:
        return jsonify({'error': 'No token found'}), 401

    try:
        headers = {'Authorization': f"Bearer {session['access_token']}"}
        response = requests.get(OAUTH_CONFIG['user_info_url'], headers=headers)

        return jsonify({
            'status': response.status_code,
            'valid': response.status_code == 200,
            'data': response.json() if response.status_code == 200 else response.text
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🧪 Тестовое OAuth2 приложение")
    print("📍 Доступно по адресу: http://localhost:3000")
    print("🔧 Настройте OAuth клиента в основном приложении:")
    print(f"   - Client ID: {OAUTH_CONFIG['client_id']}")
    print(f"   - Redirect URI: {OAUTH_CONFIG['redirect_uri']}")
    print(f"   - Scopes: {OAUTH_CONFIG['scope']}")

    app.run(debug=True, port=3000)