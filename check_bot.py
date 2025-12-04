#!/usr/bin/env python3
"""
Скрипт для диагностики проблем с ботом
"""
import json
import os
from datetime import datetime

CONFIG_FILE = '/opt/reklama_bot/bot_config.json'
if not os.path.exists(CONFIG_FILE):
    CONFIG_FILE = 'bot_config.json'

print("=" * 60)
print("🔍 ДИАГНОСТИКА БОТА")
print("=" * 60)

# 1. Проверка конфига
print("\n1️⃣ ПРОВЕРКА КОНФИГУРАЦИИ:")
print("-" * 60)
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    print(f"✅ Конфиг загружен: {CONFIG_FILE}")
    print(f"   - is_running: {config.get('is_running')}")
    print(f"   - schedule_type: {config.get('schedule_type', 'НЕ УСТАНОВЛЕНО')}")
    print(f"   - interval: {config.get('interval', 'НЕ УСТАНОВЛЕНО')} сек ({config.get('interval', 0) // 3600} часов)")
    print(f"   - schedule_days: {config.get('schedule_days', 'НЕ УСТАНОВЛЕНО')}")
    print(f"   - schedule_hours: {config.get('schedule_hours', 'НЕ УСТАНОВЛЕНО')}")
    print(f"   - recipients: {config.get('recipients', [])}")
    
    # Проверка отсутствующих полей
    required_fields = ['schedule_type', 'schedule_days', 'schedule_hours', 'schedule_even_odd']
    missing = [f for f in required_fields if f not in config]
    if missing:
        print(f"   ⚠️ Отсутствуют поля: {missing}")
        
except Exception as e:
    print(f"❌ Ошибка загрузки конфига: {e}")
    config = {}

# 2. Проверка файла изображения
print("\n2️⃣ ПРОВЕРКА ФАЙЛА ИЗОБРАЖЕНИЯ:")
print("-" * 60)
if config:
    photo_path = config.get('photo_path', '')
    if os.path.isabs(photo_path):
        full_path = photo_path
    else:
        base_dir = os.path.dirname(os.path.abspath(CONFIG_FILE))
        full_path = os.path.join(base_dir, photo_path)
    
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        print(f"✅ Файл найден: {full_path}")
        print(f"   Размер: {size} байт ({size / 1024:.1f} KB)")
    else:
        print(f"❌ Файл НЕ найден: {full_path}")
        print(f"   Путь из конфига: {photo_path}")

# 3. Проверка session файла
print("\n3️⃣ ПРОВЕРКА SESSION ФАЙЛА:")
print("-" * 60)
if config:
    session_file = config.get('session_file', '')
    if session_file:
        if os.path.isabs(session_file):
            session_path = session_file + '.session'
        else:
            base_dir = os.path.dirname(os.path.abspath(CONFIG_FILE))
            session_path = os.path.join(base_dir, session_file + '.session')
        
        if os.path.exists(session_path):
            size = os.path.getsize(session_path)
            print(f"✅ Session файл найден: {session_path}")
            print(f"   Размер: {size} байт")
            if size < 1000:
                print(f"   ⚠️ Файл слишком маленький! Возможно, требуется авторизация.")
        else:
            print(f"❌ Session файл НЕ найден: {session_path}")

# 4. Проверка расписания
print("\n4️⃣ ПРОВЕРКА РАСПИСАНИЯ:")
print("-" * 60)
now = datetime.now()
print(f"Текущее время: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"День недели: {now.strftime('%A')} ({now.weekday()})")
print(f"День месяца: {now.day} ({'четный' if now.day % 2 == 0 else 'нечетный'})")

if config:
    schedule_type = config.get('schedule_type', 'interval')
    print(f"\nРежим: {schedule_type}")
    
    if schedule_type == 'schedule':
        days = config.get('schedule_days', [])
        hours = config.get('schedule_hours', [])
        even_odd = config.get('schedule_even_odd', 'both')
        
        print(f"Дни недели: {days}")
        print(f"Часы: {hours}")
        print(f"Четность: {even_odd}")
        
        # Проверка текущего времени
        if now.weekday() in days:
            print(f"✅ Сегодня подходящий день недели")
        else:
            print(f"❌ Сегодня НЕ подходящий день недели")
        
        if now.hour in hours:
            print(f"✅ Сейчас подходящий час")
        else:
            print(f"❌ Сейчас НЕ подходящий час. Доступные: {hours}")
        
        if even_odd == 'both':
            print(f"✅ Четность не важна")
        elif even_odd == 'even' and now.day % 2 == 0:
            print(f"✅ Четный день - подходит")
        elif even_odd == 'odd' and now.day % 2 != 0:
            print(f"✅ Нечетный день - подходит")
        else:
            print(f"❌ Неподходящая четность дня")
    else:
        interval = config.get('interval', 0)
        print(f"Интервал: {interval} сек ({interval // 3600} часов)")
        print(f"⚠️ Бот будет отправлять каждые {interval // 3600} часов")

print("\n" + "=" * 60)
print("✅ Диагностика завершена")
print("=" * 60)

