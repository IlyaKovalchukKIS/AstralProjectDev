#!/usr/bin/env python
import os
import sys
import django
import base64
import requests
import uuid

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.conf import settings


def test_yookassa_auth():
    """Тестирование аутентификации в ЮKassa разными способами"""

    print("=" * 60)
    print("ТЕСТИРОВАНИЕ АУТЕНТИФИКАЦИИ ЮKASSA")
    print("=" * 60)

    shop_id = settings.YOOKASSA_SHOP_ID
    secret_key = settings.YOOKASSA_SECRET_KEY

    print(f"\n📋 Настройки из Django:")
    print(f"  YOOKASSA_SHOP_ID: {shop_id}")
    print(f"  YOOKASSA_SECRET_KEY: {secret_key[:10]}...{secret_key[-5:] if len(secret_key) > 15 else ''}")
    print(f"  YOOKASSA_TEST_MODE: {settings.YOOKASSA_TEST_MODE}")

    if not shop_id or not secret_key:
        print("\n❌ ОШИБКА: Ключи не настроены!")
        return

    # Способ 1: Basic Auth с двоеточием
    print("\n🔄 Способ 1: Basic Auth (стандартный)...")
    auth_string = f"{shop_id}:{secret_key}"
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth_base64}',
        'Idempotence-Key': str(uuid.uuid4())
    }

    data = {
        "amount": {
            "value": "100.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://example.com/success"
        },
        "capture": True,
        "description": "Тестовый платеж",
        "test": True
    }

    try:
        response = requests.post(
            'https://api.yookassa.ru/v3/payments',
            headers=headers,
            json=data,
            timeout=10
        )

        print(f"  Статус ответа: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            print("  ✅ УСПЕХ! Платеж создан")
            print(f"  ID платежа: {response.json().get('id')}")
        else:
            print(f"  ❌ ОШИБКА: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  Описание: {error_data.get('description', 'Нет описания')}")
                print(f"  Код: {error_data.get('code', 'Нет кода')}")
                print(f"  Параметр: {error_data.get('parameter', 'Нет параметра')}")
            except:
                print(f"  Текст ответа: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ ИСКЛЮЧЕНИЕ: {e}")

    # Способ 2: Basic Auth без кодирования (библиотека requests сама кодирует)
    print("\n🔄 Способ 2: Basic Auth через requests (рекомендуемый)...")

    headers2 = {
        'Content-Type': 'application/json',
        'Idempotence-Key': str(uuid.uuid4())
    }

    try:
        response2 = requests.post(
            'https://api.yookassa.ru/v3/payments',
            auth=(shop_id, secret_key),
            headers=headers2,
            json=data,
            timeout=10
        )

        print(f"  Статус ответа: {response2.status_code}")

        if response2.status_code == 200 or response2.status_code == 201:
            print("  ✅ УСПЕХ! Платеж создан")
        else:
            print(f"  ❌ ОШИБКА: {response2.status_code}")
            try:
                error_data = response2.json()
                print(f"  Описание: {error_data.get('description', 'Нет описания')}")
                print(f"  Код: {error_data.get('code', 'Нет кода')}")
            except:
                print(f"  Текст ответа: {response2.text[:200]}")
    except Exception as e:
        print(f"  ❌ ИСКЛЮЧЕНИЕ: {e}")

    # Способ 3: Пробуем получить список платежей (более простой запрос)
    print("\n🔄 Способ 3: Получение списка платежей (GET запрос)...")

    try:
        response3 = requests.get(
            'https://api.yookassa.ru/v3/payments',
            auth=(shop_id, secret_key),
            headers={'Idempotence-Key': str(uuid.uuid4())},
            timeout=10
        )

        print(f"  Статус ответа: {response3.status_code}")

        if response3.status_code == 200:
            print("  ✅ УСПЕХ! Получен список платежей")
            data = response3.json()
            print(f"  Всего платежей: {len(data.get('items', []))}")
        else:
            print(f"  ❌ ОШИБКА: {response3.status_code}")
            try:
                error_data = response3.json()
                print(f"  Описание: {error_data.get('description', 'Нет описания')}")
            except:
                print(f"  Текст ответа: {response3.text[:200]}")
    except Exception as e:
        print(f"  ❌ ИСКЛЮЧЕНИЕ: {e}")


if __name__ == "__main__":
    test_yookassa_auth()