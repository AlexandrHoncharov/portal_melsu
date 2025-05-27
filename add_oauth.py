#!/usr/bin/env python3
"""
Скрипт для автоматического создания OAuth2 клиента
"""

import requests
import json

# Настройки
API_BASE = 'http://localhost:5000/api'
ADMIN_EMAIL = 'admin@university.ru'
ADMIN_PASSWORD = 'admin123'


def get_admin_token():
    """Получение JWT токена админа"""
    print("🔑 Получаем токен админа...")

    response = requests.post(f'{API_BASE}/auth/login', json={
        'email': ADMIN_EMAIL,
        'password': ADMIN_PASSWORD
    })

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Токен получен для {data['user']['username']}")
        return data['access_token']
    else:
        print(f"❌ Ошибка получения токена: {response.text}")
        return None


def create_oauth_client(token):
    """Создание OAuth2 клиента"""
    print("🔧 Создаем OAuth2 клиента...")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    client_data = {
        'name': 'Тестовое приложение',
        'description': 'Демонстрационное приложение для тестирования OAuth2',
        'redirect_uris': 'http://localhost:3000/callback',
        'scopes': 'read:profile read:email read:roles'
    }

    response = requests.post(f'{API_BASE}/admin/oauth-clients',
                             headers=headers,
                             json=client_data)

    if response.status_code == 201:
        data = response.json()
        print("✅ OAuth2 клиент создан!")
        print(f"📋 Client ID: {data['client_id']}")
        print(f"🔐 Client Secret: {data['client_secret']}")
        return data
    else:
        print(f"❌ Ошибка создания клиента: {response.text}")
        return None


def update_test_app_config(client_data):
    """Обновление конфигурации тестового приложения"""
    print("📝 Обновляем конфигурацию тестового приложения...")

    config_template = f'''# Настройки OAuth2 (автоматически сгенерировано)
OAUTH_CONFIG = {{
    'client_id': '{client_data['client_id']}',
    'client_secret': '{client_data['client_secret']}',
    'authorization_base_url': 'http://localhost:5000/oauth/authorize',
    'token_url': 'http://localhost:5000/oauth/token',
    'user_info_url': 'http://localhost:5000/api/oauth/user',
    'redirect_uri': 'http://localhost:3000/callback',
    'scope': 'read:profile read:email read:roles'
}}'''

    try:
        # Читаем исходный файл
        with open('test_oauth_client.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # Находим и заменяем секцию с OAUTH_CONFIG
        start_marker = "# Настройки OAuth2"
        end_marker = "}"

        start_idx = content.find(start_marker)
        if start_idx != -1:
            # Ищем конец секции конфигурации
            temp_content = content[start_idx:]
            brace_count = 0
            end_idx = -1
            in_dict = False

            for i, char in enumerate(temp_content):
                if char == '{':
                    in_dict = True
                    brace_count += 1
                elif char == '}' and in_dict:
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = start_idx + i + 1
                        break

            if end_idx != -1:
                # Заменяем секцию конфигурации
                new_content = content[:start_idx] + config_template + content[end_idx:]

                # Записываем обновленный файл
                with open('test_oauth_client_updated.py', 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print("✅ Создан файл test_oauth_client_updated.py с новой конфигурацией")
                print("🚀 Теперь запустите: python test_oauth_client_updated.py")
            else:
                print("❌ Не удалось найти конец секции конфигурации")
        else:
            print("❌ Не удалось найти секцию конфигурации в файле")

    except FileNotFoundError:
        print("❌ Файл test_oauth_client.py не найден")
        print("📝 Создаем новый файл с конфигурацией...")

        with open('oauth_config.py', 'w', encoding='utf-8') as f:
            f.write(config_template)

        print("✅ Создан файл oauth_config.py с конфигурацией")


def main():
    print("🧪 Автоматическое создание OAuth2 клиента")
    print("=" * 50)

    # Получаем токен админа
    token = get_admin_token()
    if not token:
        return

    # Создаем OAuth клиента
    client_data = create_oauth_client(token)
    if not client_data:
        return

    # Обновляем конфигурацию
    update_test_app_config(client_data)

    print("\n" + "=" * 50)
    print("🎉 Готово! OAuth2 клиент создан и сконфигурирован")
    print("\n📋 Данные для ручной настройки:")
    print(f"Client ID: {client_data['client_id']}")
    print(f"Client Secret: {client_data['client_secret']}")
    print("\n🚀 Следующие шаги:")
    print("1. Запустите тестовое приложение: python test_oauth_client_updated.py")
    print("2. Откройте http://localhost:3000")
    print("3. Нажмите 'Войти через систему университета'")
    print("4. Протестируйте OAuth2 flow!")


if __name__ == '__main__':
    main()