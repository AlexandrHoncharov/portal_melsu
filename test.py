import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Конфигурация (не храни пароли в коде в проде!)
SMTP_HOST = "email.melsu.ru"
SMTP_PORT_TLS = 587  # STARTTLS
SMTP_PORT_SSL = 465  # SSL
SMTP_USER = "help@melsu.ru"
SMTP_PASS = "fl_92||LII_O0"  # Рассмотрите использование переменных окружения или файла конфигурации
RECIPIENT = "sanumxxx@yandex.ru"  # Укажите сюда свою почту для теста

def send_email(subject, html_body, use_ssl=False):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT
    msg['Subject'] = subject

    msg.attach(MIMEText(html_body, 'html'))

    # Создаем менее строгий SSL-контекст для целей тестирования.
    # ВНИМАНИЕ: Это отключает проверку сертификата и НЕБЕЗОПАСНО для продакшена.
    # Используется здесь для обхода потенциальной FileNotFoundError от create_default_context()
    # и проблем с проверкой сертификата на сервере.
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # Более общая версия протокола
        context.check_hostname = False  # Не проверять имя хоста в сертификате
        context.verify_mode = ssl.CERT_NONE  # НЕ ПРОВЕРЯТЬ сертификат сервера
    except Exception as e:
        print(f"⚠️ Ошибка при создании SSL контекста: {e}")
        print("Продолжаем без пользовательского SSL контекста, используя стандартные настройки по умолчанию.")
        # Если создание SSLContext не удалось, пробуем стандартный (хотя это может вернуть FileNotFoundError)
        context = ssl.create_default_context()


    try:
        if use_ssl:
            print(f"🔐 Используем SMTP с SSL ({SMTP_HOST}:{SMTP_PORT_SSL})")
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT_SSL, context=context, timeout=20) as server:
                server.set_debuglevel(1)
                print("Логин...")
                server.login(SMTP_USER, SMTP_PASS)
                print("Отправка сообщения...")
                server.send_message(msg)
        else:
            print(f"🔐 Используем SMTP с TLS ({SMTP_HOST}:{SMTP_PORT_TLS})")
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT_TLS, timeout=20) as server:
                server.set_debuglevel(1)
                print("Приветствие (EHLO)...")
                server.ehlo() # Первоначальное EHLO
                print("Старт TLS...")
                # Передаем пользовательский context в starttls
                server.starttls(context=context)
                print("Повторное приветствие (EHLO) после TLS...")
                server.ehlo() # EHLO снова после TLS
                print("Логин...")
                server.login(SMTP_USER, SMTP_PASS)
                print("Отправка сообщения...")
                server.send_message(msg)

        print("✅ Письмо успешно отправлено")
        return True

    except smtplib.SMTPAuthenticationError as e:
        error_msg = e.smtp_error.decode('utf-8', errors='ignore') if hasattr(e.smtp_error, 'decode') else str(e.smtp_error)
        print(f"❌ Ошибка авторизации: {e.smtp_code} — {error_msg}")
    except smtplib.SMTPConnectError as e:
        print(f"❌ Ошибка подключения к серверу: {e}")
    except smtplib.SMTPServerDisconnected as e:
        print(f"❌ Сервер неожиданно разорвал соединение: {e}")
    except smtplib.SMTPException as e:
        print(f"❌ Общая SMTP ошибка: {e}")
    except ConnectionResetError as e:
        print(f"❌ Соединение сброшено удаленным хостом: {e}")
    except ssl.SSLError as e:
        print(f"❌ SSL ошибка: {e}")
    except TimeoutError as e:
        print(f"❌ Ошибка тайм-аута: {e}")
    except FileNotFoundError as e: # Явно ловим FileNotFoundError
        print(f"❌ Ошибка FileNotFoundError (вероятно, не найдены CA сертификаты): {e}")
    except Exception as e:
        print(f"❌ Другая ошибка: {type(e).__name__} — {e}")

    return False


html_content = """
<html>
    <body>
        <h2>Тестовое письмо (исправленный код)</h2>
        <p>Проверка отправки через SMTP сервер с отключенной проверкой сертификата.</p>
    </body>
</html>
"""

# Сначала пробуем через TLS (587)
print("--- Попытка через TLS (порт 587) ---")
success = send_email("Проверка SMTP TLS (melsu.ru - испр.)", html_content, use_ssl=False)

# Если не получилось — пробуем через SSL (465)
if not success:
    print("\n--- Попытка через SSL (порт 465) ---")
    send_email("Проверка SMTP SSL (melsu.ru - испр.)", html_content, use_ssl=True)

print("\nПроцесс завершен.")