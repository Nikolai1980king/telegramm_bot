from telethon.sync import TelegramClient
from telethon import functions, types
from telethon.errors import (
    UserBlockedError, FloodWaitError, PeerFloodError,
    InputUserDeactivatedError, UsernameNotOccupiedError,
    ChatWriteForbiddenError, TimeoutError as TelethonTimeoutError
)
import os
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
import json
import threading
import asyncio
import logging
import hashlib
import secrets
from collections import defaultdict

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Секретный ключ для сессий

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Конфигурационный файл
CONFIG_FILE = os.path.join(BASE_DIR, 'bot_config.json')

# Файл статистики
STATISTICS_FILE = os.path.join(BASE_DIR, 'statistics.json')

# Загрузка конфигурации по умолчанию
DEFAULT_CONFIG = {
    'api_id': '27375139',
    'api_hash': '66e1bc627b8dda02e2bb35ea44fde4cf',
    'phone_number': '+79140024032',
    'recipients': ['@Nikolai198019'],
    'interval': 32400,  # 9 часов
    'photo_path': os.path.join(BASE_DIR, 'image', 'cart_1.png'),
    'caption': '''здесь будет видеоролик -переходи в приложение @znakomstva_v_kafe_bot''',
    'is_running': False,
    'session_file': os.path.join(BASE_DIR, 'session_name'),
    # Настройки расписания
    'schedule_type': 'interval',  # 'interval' или 'schedule'
    'schedule_days': [0, 1, 2, 3, 4, 5, 6],  # Дни недели: 0=понедельник, 6=воскресенье
    'schedule_hours': [9, 12, 18],  # Часы отправки (0-23)
    'schedule_even_odd': 'both',  # 'both', 'even', 'odd'
    # Защита веб-интерфейса
    'web_password': ''  # Пароль для доступа к веб-интерфейсу (пусто = без пароля)
}


def normalize_path(path):
    """Преобразует относительный путь в абсолютный относительно BASE_DIR"""
    if not path:
        return path
    if os.path.isabs(path):
        return path
    return os.path.join(BASE_DIR, path)


def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Обновляем конфиг, если добавлены новые поля
            for key in DEFAULT_CONFIG:
                if key not in config:
                    config[key] = DEFAULT_CONFIG[key]
            # Нормализуем пути (если они относительные, делаем абсолютными)
            if 'photo_path' in config:
                config['photo_path'] = normalize_path(config['photo_path'])
            if 'session_file' in config and not os.path.isabs(config.get('session_file', '')):
                config['session_file'] = normalize_path(config['session_file'])
            return config
    except (FileNotFoundError, json.JSONDecodeError):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


def load_statistics():
    """Загружает статистику отправки сообщений"""
    try:
        if os.path.exists(STATISTICS_FILE):
            with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"⚠️ Ошибка загрузки статистики: {e}")
    
    # Возвращаем структуру по умолчанию
    return {
        'total_sent': 0,
        'total_failed': 0,
        'total_blocked': 0,
        'recipients': {},
        'last_send_time': None,
        'session_start': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'errors_history': []
    }


def save_statistics(stats):
    """Сохраняет статистику отправки сообщений"""
    try:
        with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения статистики: {e}")


def reset_statistics():
    """Сбрасывает всю статистику отправки сообщений"""
    try:
        default_stats = {
            'total_sent': 0,
            'total_failed': 0,
            'total_blocked': 0,
            'recipients': {},
            'last_send_time': None,
            'session_start': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'errors_history': []
        }
        save_statistics(default_stats)
        logger.info("🔄 Статистика сброшена")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при сбросе статистики: {e}")
        return False


def get_error_type(error):
    """Определяет тип ошибки для статистики"""
    error_str = str(error)
    error_type = type(error).__name__
    
    if isinstance(error, UserBlockedError):
        return 'blocked', 'Пользователь заблокировал вас'
    elif isinstance(error, FloodWaitError):
        wait_seconds = getattr(error, 'seconds', 0)
        return 'flood_wait', f'Лимит отправки, ждать {wait_seconds} сек'
    elif isinstance(error, PeerFloodError):
        return 'peer_flood', 'Слишком много запросов к пользователю'
    elif isinstance(error, InputUserDeactivatedError):
        return 'deactivated', 'Пользователь удалил аккаунт'
    elif isinstance(error, UsernameNotOccupiedError):
        return 'not_found', 'Пользователь не найден'
    elif isinstance(error, ChatWriteForbiddenError):
        return 'forbidden', 'Нет прав на отправку'
    elif isinstance(error, TelethonTimeoutError):
        return 'timeout', 'Таймаут соединения'
    elif 'database is locked' in error_str.lower() or ('locked' in error_str.lower() and 'database' in error_str.lower()):
        return 'database_locked', 'База данных заблокирована'
    elif 'Connection' in error_type or 'network' in error_str.lower():
        return 'connection', 'Проблема с сетью'
    else:
        return 'unknown', f'Неизвестная ошибка: {error_str[:100]}'


def hash_password(password):
    """Хеширует пароль для безопасного хранения"""
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password, password_hash):
    """Проверяет пароль"""
    return hash_password(password) == password_hash


def login_required(f):
    """Декоратор для защиты маршрутов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = load_config()
        # Если пароль не установлен - доступ открыт
        if not config.get('web_password'):
            return f(*args, **kwargs)
        
        # Проверяем авторизацию
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def check_schedule(config):
    """Проверяет, можно ли отправлять сообщение по расписанию"""
    now = datetime.now()
    current_day = now.weekday()  # 0=понедельник, 6=воскресенье
    current_hour = now.hour
    current_date = now.day
    
    # Проверка типа расписания
    if config.get('schedule_type') == 'schedule':
        # Проверка дня недели
        if current_day not in config.get('schedule_days', []):
            return False
        
        # Проверка часа
        if current_hour not in config.get('schedule_hours', []):
            return False
        
        # Проверка четности даты
        even_odd = config.get('schedule_even_odd', 'both')
        if even_odd == 'even' and current_date % 2 != 0:
            return False
        if even_odd == 'odd' and current_date % 2 == 0:
            return False
    
    return True


def get_next_send_time(config):
    """Вычисляет время следующей отправки по расписанию"""
    if config.get('schedule_type') == 'interval':
        return None  # Используется интервал
    
    now = datetime.now()
    schedule_hours = sorted(config.get('schedule_hours', []))
    schedule_days = config.get('schedule_days', [])
    even_odd = config.get('schedule_even_odd', 'both')
    
    # Ищем следующий час сегодня
    for hour in schedule_hours:
        if hour > now.hour and now.weekday() in schedule_days:
            next_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            # Временная проверка четности для этого времени
            temp_config = config.copy()
            temp_config['schedule_type'] = 'schedule'
            # Создаем временный datetime для проверки
            test_time = next_time
            if even_odd == 'even' and test_time.day % 2 != 0:
                continue
            if even_odd == 'odd' and test_time.day % 2 == 0:
                continue
            return next_time
    
    # Ищем следующий день
    for day_offset in range(1, 15):  # Проверяем до 2 недель вперед
        next_day = now + timedelta(days=day_offset)
        if next_day.weekday() in schedule_days:
            # Проверяем четность даты
            if even_odd == 'even' and next_day.day % 2 != 0:
                continue
            if even_odd == 'odd' and next_day.day % 2 == 0:
                continue
            
            for hour in schedule_hours:
                next_time = next_day.replace(hour=hour, minute=0, second=0, microsecond=0)
                return next_time
    
    return None


class TelegramBot:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.loop = asyncio.new_event_loop()
        self.stop_flag = False
        self.statistics = load_statistics()
        session_file = config.get('session_file', 'session_name')
        # Если путь относительный, делаем его относительно BASE_DIR
        if not os.path.isabs(session_file):
            self.session_file = os.path.join(BASE_DIR, session_file)
        else:
            self.session_file = session_file

    async def _initialize_client(self):
        # Сначала отключаем существующий клиент, если он есть
        if self.client:
            try:
                if self.client.is_connected():
                    await self.client.disconnect()
                    logger.info("🔌 Существующий клиент отключен")
                await asyncio.sleep(1)  # Даем время на закрытие соединения
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при отключении существующего клиента: {e}")
        
        # Удаляем lock файлы перед подключением
        lock_files = [
            self.session_file + '-journal',
            self.session_file + '-wal',
            self.session_file + '-shm'  # Добавляем shm файл
        ]
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info(f"🗑️ Удален lock файл: {lock_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось удалить lock файл {lock_file}: {e}")
        
        # Создаем новый клиент с настройками для предотвращения блокировки
        self.client = TelegramClient(
            self.session_file,
            self.config['api_id'],
            self.config['api_hash'],
            connection_retries=3,
            retry_delay=2,
            timeout=30
        )
        
        # Повторные попытки подключения при ошибке блокировки базы данных
        max_retries = 5  # Увеличиваем количество попыток
        for attempt in range(max_retries):
            try:
                await self.client.connect()
                # Проверяем, что подключение действительно установлено
                if self.client.is_connected():
                    break
            except Exception as e:
                error_str = str(e).lower()
                if ('database is locked' in error_str or 'locked' in error_str) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Увеличиваем время ожидания с каждой попыткой
                    logger.warning(f"⚠️ Попытка {attempt + 1}/{max_retries}: база данных заблокирована, жду {wait_time} секунд...")
                    await asyncio.sleep(wait_time)
                    
                    # Попробуем удалить lock файлы еще раз
                    for lock_file in lock_files:
                        if os.path.exists(lock_file):
                            try:
                                os.remove(lock_file)
                                logger.info(f"🗑️ Повторное удаление lock файла: {lock_file}")
                            except Exception as e2:
                                logger.warning(f"⚠️ Не удалось удалить {lock_file}: {e2}")
                    
                    # Если клиент был создан, но не подключен, создаем новый
                    if self.client and not self.client.is_connected():
                        try:
                            await self.client.disconnect()
                        except:
                            pass
                        self.client = TelegramClient(
                            self.session_file,
                            self.config['api_id'],
                            self.config['api_hash'],
                            connection_retries=3,
                            retry_delay=2,
                            timeout=30
                        )
                else:
                    logger.error(f"❌ Ошибка подключения: {e}")
                    raise

        if not await self.client.is_user_authorized():
            logger.info("📱 Требуется авторизация...")
            logger.info(f"📞 Отправка кода на номер: {self.config['phone_number']}")
            
            # Запрашиваем код авторизации
            await self.client.send_code_request(self.config['phone_number'])
            
            # Проверяем, есть ли доступ к stdin (локальный запуск)
            import sys
            if sys.stdin.isatty():
                # Локальный запуск - можно ввести код
                code = input("🔐 Введите код из Telegram (придет в приложение Telegram на ваш телефон): ")
                await self.client.sign_in(self.config['phone_number'], code)
                logger.info("✅ Авторизация успешна! Session файл создан.")
            else:
                # Запуск на сервере без доступа к консоли
                logger.error("❌ Требуется авторизация! Session файл не авторизован.")
                logger.error("💡 РЕШЕНИЕ: Запустите бота локально один раз для авторизации, затем загрузите session файл на сервер.")
                raise Exception("Требуется авторизация. Запустите бота локально для создания авторизованного session файла.")

    async def _send_messages(self):
        try:
            await self._initialize_client()
            logger.info("✅ Авторизация успешна!")

            while not self.stop_flag:
                # Перезагружаем конфиг перед каждым циклом для применения изменений
                self.config = load_config()
                
                # Проверяем, не был ли бот остановлен через веб-интерфейс
                if not self.config.get('is_running', False):
                    logger.info("🛑 Бот остановлен через веб-интерфейс")
                    break
                
                # Нормализуем пути после перезагрузки конфига
                self.config['photo_path'] = normalize_path(self.config['photo_path'])
                if 'session_file' in self.config and not os.path.isabs(self.config.get('session_file', '')):
                    self.config['session_file'] = normalize_path(self.config['session_file'])
                
                if not os.path.exists(self.config['photo_path']):
                    logger.error(f"⚠️ Файл не найден: {self.config['photo_path']}")
                    await asyncio.sleep(60)
                    continue

                # Проверка расписания
                if self.config.get('schedule_type') == 'schedule':
                    if not check_schedule(self.config):
                        # Вычисляем время следующей отправки
                        next_time = get_next_send_time(self.config)
                        if next_time:
                            wait_seconds = (next_time - datetime.now()).total_seconds()
                            if wait_seconds > 0:
                                logger.info(f"⏰ Следующая отправка по расписанию: {next_time.strftime('%H:%M %d.%m.%Y')}")
                                # Ждем до следующего времени отправки (проверяем каждую минуту)
                                while wait_seconds > 0 and not self.stop_flag:
                                    await asyncio.sleep(min(60, wait_seconds))
                                    wait_seconds = (next_time - datetime.now()).total_seconds()
                                if self.stop_flag:
                                    break
                        else:
                            # Если не найдено следующее время, ждем час и проверяем снова
                            await asyncio.sleep(3600)
                            continue
                    # Если расписание позволяет - отправляем

                current_time = datetime.now().strftime('%H:%M %d.%m.%Y')
                # Форматируем caption только если там есть {datetime}
                caption = self.config['caption']
                if '{datetime}' in caption:
                    caption = caption.format(datetime=current_time)

                # Проверяем подключение перед отправкой
                if not self.client or not self.client.is_connected():
                    logger.warning("⚠️ Клиент не подключен, переподключаюсь...")
                    await self._initialize_client()
                
                # Статистика текущей отправки
                send_stats = {
                    'success': [],
                    'failed': [],
                    'blocked': [],
                    'errors': {}
                }
                
                for user in self.config['recipients']:
                    if self.stop_flag:
                        break
                    try:
                        await self.client.send_file(
                            entity=user,
                            file=self.config['photo_path'],
                            caption=caption,
                            parse_mode='html'
                        )
                        # Успешная отправка
                        logger.info(f"✅ Отправлено для {user} в {current_time}")
                        send_stats['success'].append(user)
                        
                        # Обновляем статистику
                        if user not in self.statistics['recipients']:
                            self.statistics['recipients'][user] = {
                                'success': 0,
                                'failed': 0,
                                'blocked': False,
                                'last_success': None,
                                'last_error': None,
                                'errors': []
                            }
                        
                        self.statistics['recipients'][user]['success'] += 1
                        self.statistics['recipients'][user]['last_success'] = current_time
                        self.statistics['total_sent'] += 1
                        
                    except FloodWaitError as e:
                        # Лимит отправки - нужно подождать
                        wait_seconds = getattr(e, 'seconds', 0)
                        error_type, error_msg = get_error_type(e)
                        logger.warning(f"⏱️ Лимит отправки для {user}: ждать {wait_seconds} секунд")
                        
                        send_stats['failed'].append(user)
                        send_stats['errors'][user] = error_msg
                        
                        if user not in self.statistics['recipients']:
                            self.statistics['recipients'][user] = {
                                'success': 0,
                                'failed': 0,
                                'blocked': False,
                                'last_success': None,
                                'last_error': None,
                                'errors': []
                            }
                        
                        self.statistics['recipients'][user]['failed'] += 1
                        self.statistics['recipients'][user]['last_error'] = current_time
                        if error_type not in self.statistics['recipients'][user]['errors']:
                            self.statistics['recipients'][user]['errors'].append(error_type)
                        self.statistics['total_failed'] += 1
                        
                        # Ждем указанное время
                        if wait_seconds > 0:
                            logger.info(f"⏳ Ожидание {wait_seconds} секунд из-за лимита...")
                            await asyncio.sleep(min(wait_seconds, 300))  # Максимум 5 минут
                        
                    except UserBlockedError:
                        # Пользователь заблокировал
                        error_type, error_msg = get_error_type(UserBlockedError())
                        logger.error(f"🔒 Пользователь {user} заблокировал вас")
                        
                        send_stats['blocked'].append(user)
                        send_stats['failed'].append(user)
                        send_stats['errors'][user] = error_msg
                        
                        if user not in self.statistics['recipients']:
                            self.statistics['recipients'][user] = {
                                'success': 0,
                                'failed': 0,
                                'blocked': False,
                                'last_success': None,
                                'last_error': None,
                                'errors': []
                            }
                        
                        self.statistics['recipients'][user]['blocked'] = True
                        self.statistics['recipients'][user]['failed'] += 1
                        self.statistics['recipients'][user]['last_error'] = current_time
                        if 'blocked' not in self.statistics['recipients'][user]['errors']:
                            self.statistics['recipients'][user]['errors'].append('blocked')
                        self.statistics['total_blocked'] += 1
                        self.statistics['total_failed'] += 1
                        
                    except Exception as e:
                        # Другие ошибки
                        error_str = str(e).lower()
                        
                        # Если ошибка связана с блокировкой базы данных, пытаемся переподключиться
                        if 'database is locked' in error_str or 'locked' in error_str:
                            logger.warning(f"⚠️ Обнаружена блокировка базы данных для {user}, пытаюсь переподключиться...")
                            try:
                                # Отключаем клиент
                                if self.client and self.client.is_connected():
                                    await self.client.disconnect()
                                    await asyncio.sleep(2)
                                
                                # Переподключаемся
                                await self._initialize_client()
                                logger.info("✅ Переподключение успешно, повторяю отправку...")
                                
                                # Пытаемся отправить снова
                                try:
                                    await self.client.send_file(
                                        entity=user,
                                        file=self.config['photo_path'],
                                        caption=caption,
                                        parse_mode='html'
                                    )
                                    logger.info(f"✅ Отправлено для {user} в {current_time} (после переподключения)")
                                    send_stats['success'].append(user)
                                    
                                    if user not in self.statistics['recipients']:
                                        self.statistics['recipients'][user] = {
                                            'success': 0,
                                            'failed': 0,
                                            'blocked': False,
                                            'last_success': None,
                                            'last_error': None,
                                            'errors': []
                                        }
                                    
                                    self.statistics['recipients'][user]['success'] += 1
                                    self.statistics['recipients'][user]['last_success'] = current_time
                                    self.statistics['total_sent'] += 1
                                    continue  # Переходим к следующему пользователю
                                except Exception as retry_e:
                                    logger.error(f"❌ Ошибка при повторной отправке для {user}: {retry_e}")
                                    error_type, error_msg = get_error_type(retry_e)
                            except Exception as reconnect_e:
                                logger.error(f"❌ Ошибка переподключения: {reconnect_e}")
                                error_type, error_msg = get_error_type(e)
                        else:
                            error_type, error_msg = get_error_type(e)
                        
                        logger.error(f"❌ Ошибка для {user}: {error_msg}")
                        
                        send_stats['failed'].append(user)
                        send_stats['errors'][user] = error_msg
                        
                        if user not in self.statistics['recipients']:
                            self.statistics['recipients'][user] = {
                                'success': 0,
                                'failed': 0,
                                'blocked': False,
                                'last_success': None,
                                'last_error': None,
                                'errors': []
                            }
                        
                        self.statistics['recipients'][user]['failed'] += 1
                        self.statistics['recipients'][user]['last_error'] = current_time
                        if error_type not in self.statistics['recipients'][user]['errors']:
                            self.statistics['recipients'][user]['errors'].append(error_type)
                        self.statistics['total_failed'] += 1
                        
                        # Добавляем в историю ошибок
                        self.statistics['errors_history'].append({
                            'time': current_time,
                            'recipient': user,
                            'error_type': error_type,
                            'error_msg': error_msg
                        })
                        # Оставляем только последние 100 ошибок
                        if len(self.statistics['errors_history']) > 100:
                            self.statistics['errors_history'] = self.statistics['errors_history'][-100:]
                
                # Обновляем время последней отправки
                self.statistics['last_send_time'] = current_time
                
                # Сохраняем статистику
                save_statistics(self.statistics)
                
                # Логируем итоги отправки
                total = len(self.config['recipients'])
                success_count = len(send_stats['success'])
                failed_count = len(send_stats['failed'])
                blocked_count = len(send_stats['blocked'])
                
                logger.info(f"📊 Итоги отправки: ✅ {success_count}/{total} успешно, ❌ {failed_count} ошибок, 🔒 {blocked_count} заблокировано")
                
                if send_stats['blocked']:
                    logger.warning(f"🔒 Заблокированные пользователи: {', '.join(send_stats['blocked'])}")
                
                if send_stats['errors']:
                    logger.warning(f"⚠️ Ошибки: {', '.join([f'{u}: {e}' for u, e in send_stats['errors'].items()])}")

                if self.stop_flag:
                    break

                # Определяем время следующей отправки
                if self.config.get('schedule_type') == 'schedule':
                    next_time = get_next_send_time(self.config)
                    if next_time:
                        wait_seconds = (next_time - datetime.now()).total_seconds()
                        logger.info(f"⏰ Следующая отправка по расписанию: {next_time.strftime('%H:%M %d.%m.%Y')}")
                        while wait_seconds > 0 and not self.stop_flag:
                            await asyncio.sleep(min(60, wait_seconds))
                            wait_seconds = (next_time - datetime.now()).total_seconds()
                    else:
                        await asyncio.sleep(3600)  # Ждем час, если не найдено время
                else:
                    # Режим интервала
                    logger.info(f"⏳ Следующая отправка через {self.config['interval'] // 3600} часов...")
                    # Разбиваем длительный сон на короткие интервалы для быстрой остановки
                    sleep_time = 0
                    while sleep_time < self.config['interval'] and not self.stop_flag:
                        await asyncio.sleep(min(60, self.config['interval'] - sleep_time))
                        sleep_time += 60

        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"❌ Критическая ошибка: {str(e)}")
            
            # Если ошибка связана с блокировкой базы данных, пытаемся исправить
            if 'database is locked' in error_str or 'locked' in error_str:
                logger.warning("⚠️ Критическая ошибка: база данных заблокирована, пытаюсь исправить...")
                # Удаляем lock файлы
                lock_files = [
                    self.session_file + '-journal',
                    self.session_file + '-wal',
                    self.session_file + '-shm'
                ]
                for lock_file in lock_files:
                    if os.path.exists(lock_file):
                        try:
                            os.remove(lock_file)
                            logger.info(f"🗑️ Удален lock файл: {lock_file}")
                        except Exception as e2:
                            logger.warning(f"⚠️ Не удалось удалить {lock_file}: {e2}")
        finally:
            if self.client:
                try:
                    if self.client.is_connected():
                        await self.client.disconnect()
                        logger.info("🔌 Клиент отключен")
                    await asyncio.sleep(0.5)  # Даем время на закрытие соединения
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при отключении: {str(e)}")
                finally:
                    # Убеждаемся, что lock файлы удалены
                    lock_files = [
                        self.session_file + '-journal',
                        self.session_file + '-wal',
                        self.session_file + '-shm'
                    ]
                    for lock_file in lock_files:
                        if os.path.exists(lock_file):
                            try:
                                os.remove(lock_file)
                            except:
                                pass
            self.config['is_running'] = False
            save_config(self.config)

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._send_messages())

    def stop(self):
        self.stop_flag = True
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


# Глобальные переменные для управления ботом
bot_instance = None
bot_thread = None


def bot_worker():
    global bot_instance
    config = load_config()
    bot_instance = TelegramBot(config)
    bot_instance.run()
    bot_instance = None


@app.route('/login', methods=['GET', 'POST'])
def login():
    config = load_config()
    
    # Если пароль не установлен - показываем сообщение
    if not config.get('web_password'):
        if request.method == 'POST':
            # Установка пароля через форму входа (если нужно)
            return redirect(url_for('index'))
        return render_template('login.html', no_password=True)
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        if check_password(password, config['web_password']):
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Неверный пароль')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/statistics')
@login_required
def statistics():
    """API для получения статистики"""
    try:
        stats = load_statistics()
        
        # Вычисляем процент успешности
        total_attempts = stats['total_sent'] + stats['total_failed']
        success_rate = (stats['total_sent'] / total_attempts * 100) if total_attempts > 0 else 0
        
        # Получаем список заблокированных
        blocked_users = [
            user for user, data in stats['recipients'].items()
            if data.get('blocked', False)
        ]
        
        # Получаем проблемных пользователей (много ошибок)
        problematic_users = [
            {
                'user': user,
                'failed': data['failed'],
                'success': data['success'],
                'errors': data.get('errors', []),
                'last_error': data.get('last_error')
            }
            for user, data in stats['recipients'].items()
            if data['failed'] > data['success'] and data['failed'] > 2
        ]
        
        return jsonify({
            'total_sent': stats.get('total_sent', 0),
            'total_failed': stats.get('total_failed', 0),
            'total_blocked': stats.get('total_blocked', 0),
            'success_rate': round(success_rate, 2),
            'blocked_users': blocked_users,
            'problematic_users': problematic_users,
            'last_send_time': stats.get('last_send_time'),
            'recipients_count': len(stats.get('recipients', {})),
            'recent_errors': stats.get('errors_history', [])[-10:]  # Последние 10 ошибок
        })
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке статистики: {e}")
        return jsonify({
            'error': str(e),
            'total_sent': 0,
            'total_failed': 0,
            'total_blocked': 0,
            'success_rate': 0,
            'blocked_users': [],
            'problematic_users': [],
            'last_send_time': None,
            'recipients_count': 0,
            'recent_errors': []
        }), 500


@app.route('/statistics/export')
@login_required
def export_statistics():
    """Экспорт статистики в JSON"""
    stats = load_statistics()
    return jsonify(stats)


@app.route('/statistics/reset', methods=['POST'])
@login_required
def reset_statistics_endpoint():
    """Сброс всей статистики"""
    try:
        if reset_statistics():
            return jsonify({'success': True, 'message': 'Статистика успешно сброшена'})
        else:
            return jsonify({'success': False, 'message': 'Ошибка при сбросе статистики'}), 500
    except Exception as e:
        logger.error(f"❌ Ошибка при сбросе статистики: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/')
@login_required
def index():
    global bot_thread
    config = load_config()
    
    # Синхронизируем статус с реальным состоянием потока
    if config.get('is_running'):
        if bot_thread is None or not bot_thread.is_alive():
            # Бот должен быть запущен, но поток не работает - обновляем статус
            config['is_running'] = False
            save_config(config)
            logger.info("🔄 Статус синхронизирован: бот был остановлен")
    
    # Загружаем статистику
    statistics = load_statistics()
    
    hours = config['interval'] // 3600
    return render_template('index.html', config=config, hours=hours, statistics=statistics)


@app.route('/update', methods=['POST'])
@login_required
def update():
    config = load_config()

    config['api_id'] = request.form.get('api_id', config['api_id'])
    config['api_hash'] = request.form.get('api_hash', config['api_hash'])
    config['phone_number'] = request.form.get('phone_number', config['phone_number'])
    config['photo_path'] = request.form.get('photo_path', config['photo_path'])
    config['caption'] = request.form.get('caption', config['caption'])
    config['session_file'] = request.form.get('session_file', config.get('session_file', 'session_name'))

    recipients = request.form.get('recipients', '')
    config['recipients'] = [r.strip() for r in recipients.replace(',', '\n').split('\n') if r.strip()]

    try:
        hours = float(request.form.get('interval_hours', config['interval'] / 3600))
        config['interval'] = int(hours * 3600)
    except ValueError:
        pass

    # Настройки расписания
    config['schedule_type'] = request.form.get('schedule_type', 'interval')
    
    # Дни недели
    schedule_days = []
    days_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
    for day_key, day_num in days_map.items():
        if request.form.get(f'schedule_day_{day_key}'):
            schedule_days.append(day_num)
    config['schedule_days'] = schedule_days if schedule_days else [0, 1, 2, 3, 4, 5, 6]
    
    # Часы
    schedule_hours_str = request.form.get('schedule_hours', '')
    if schedule_hours_str:
        try:
            config['schedule_hours'] = [int(h.strip()) for h in schedule_hours_str.split(',') if h.strip().isdigit()]
        except ValueError:
            config['schedule_hours'] = [9, 12, 18]
    else:
        config['schedule_hours'] = [9, 12, 18]
    
    # Четные/нечетные даты
    config['schedule_even_odd'] = request.form.get('schedule_even_odd', 'both')

    # Пароль для веб-интерфейса
    new_password = request.form.get('web_password', '').strip()
    if new_password:
        config['web_password'] = hash_password(new_password)
    elif request.form.get('web_password_clear') == '1':
        config['web_password'] = ''

    save_config(config)
    return redirect(url_for('index'))


@app.route('/control', methods=['POST'])
@login_required
def control():
    global bot_thread, bot_instance

    config = load_config()
    action = request.form.get('action')

    if action == 'start' and not config['is_running']:
        config['is_running'] = True
        save_config(config)
        if bot_thread is None or not bot_thread.is_alive():
            bot_thread = threading.Thread(target=bot_worker, daemon=True)
            bot_thread.start()
            logger.info("Бот запущен")
    elif action == 'stop' and config['is_running']:
        config['is_running'] = False
        save_config(config)
        # Останавливаем бота если он запущен
        if bot_instance:
            bot_instance.stop()
            logger.info("Бот остановлен")
        else:
            logger.info("Бот остановлен (флаг установлен)")

    return redirect(url_for('index'))


def ensure_template_exists():
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)

    index_html = os.path.join(templates_dir, 'index.html')
    if not os.path.exists(index_html):
        with open(index_html, 'w', encoding='utf-8') as f:
            f.write('''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Управление Telegram ботом</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], textarea, input[type="number"] {
            width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;
        }
        textarea { height: 200px; }
        button { background: #4CAF50; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; }
        button.stop { background: #f44336; }
        .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .status.running { background: #dff0d8; color: #3c763d; }
        .status.stopped { background: #f2dede; color: #a94442; }
        .logs { background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; white-space: pre; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Управление Telegram ботом</h1>

        <div class="status {{ 'running' if config.is_running else 'stopped' }}">
            Статус: {{ 'Работает' if config.is_running else 'Остановлен' }}
        </div>

        <form action="/control" method="post">
            {% if not config.is_running %}
                <button type="submit" name="action" value="start">Запустить бота</button>
            {% else %}
                <button type="submit" name="action" value="stop" class="stop">Остановить бота</button>
            {% endif %}
        </form>

        <h2>Настройки бота</h2>
        <form action="/update" method="post">
            <div class="form-group">
                <label for="api_id">API ID:</label>
                <input type="text" id="api_id" name="api_id" value="{{ config.api_id }}" required>
            </div>

            <div class="form-group">
                <label for="api_hash">API Hash:</label>
                <input type="text" id="api_hash" name="api_hash" value="{{ config.api_hash }}" required>
            </div>

            <div class="form-group">
                <label for="phone_number">Номер телефона:</label>
                <input type="text" id="phone_number" name="phone_number" value="{{ config.phone_number }}" required>
            </div>

            <div class="form-group">
                <label for="session_file">Имя session файла:</label>
                <input type="text" id="session_file" name="session_file" value="{{ config.session_file }}" required>
            </div>

            <div class="form-group">
                <label for="photo_path">Путь к изображению:</label>
                <input type="text" id="photo_path" name="photo_path" value="{{ config.photo_path }}" required>
            </div>

            <div class="form-group">
                <label for="interval_hours">Интервал отправки (часы):</label>
                <input type="number" id="interval_hours" name="interval_hours" value="{{ hours }}" step="0.5" min="0.5" required>
            </div>

            <div class="form-group">
                <label for="recipients">Получатели (каждый с новой строки или через запятую):</label>
                <textarea id="recipients" name="recipients" required>{{ '\\n'.join(config.recipients) }}</textarea>
            </div>

            <div class="form-group">
                <label for="caption">Текст сообщения:</label>
                <textarea id="caption" name="caption" required>{{ config.caption }}</textarea>
                <small>Используйте {datetime} для вставки даты и времени</small>
            </div>

            <button type="submit">Сохранить настройки</button>
        </form>

        <h2>Логи</h2>
        <div class="logs">
            Последние события будут отображаться здесь...
        </div>
    </div>
</body>
</html>''')


if __name__ == '__main__':
    ensure_template_exists()
    
    # Автозапуск бота, если в конфиге is_running = True
    config = load_config()
    if config.get('is_running'):
        if bot_thread is None or not bot_thread.is_alive():
            logger.info("🚀 Автозапуск бота (is_running = True)...")
            bot_thread = threading.Thread(target=bot_worker, daemon=True)
            bot_thread.start()
        else:
            logger.info("✅ Бот уже запущен")
    
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)