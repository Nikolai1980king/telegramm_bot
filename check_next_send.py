#!/usr/bin/env python3
"""
Скрипт для проверки времени следующей отправки сообщений
"""
import json
import os
from datetime import datetime, timedelta

CONFIG_FILE = '/opt/reklama_bot/bot_config.json'
if not os.path.exists(CONFIG_FILE):
    CONFIG_FILE = 'bot_config.json'

print("=" * 60)
print("📅 ВРЕМЯ СЛЕДУЮЩЕЙ ОТПРАВКИ")
print("=" * 60)

# Загрузить конфиг
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except Exception as e:
    print(f"❌ Ошибка загрузки конфига: {e}")
    exit(1)

now = datetime.now()
print(f"\n🕐 Текущее время: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📅 День недели: {['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][now.weekday()]} ({now.weekday()})")
print(f"📆 День месяца: {now.day} ({'четный' if now.day % 2 == 0 else 'нечетный'})")

schedule_type = config.get('schedule_type', 'interval')
print(f"\n📋 Режим работы: {schedule_type}")

if schedule_type == 'schedule':
    schedule_days = config.get('schedule_days', [])
    schedule_hours = sorted(config.get('schedule_hours', []))
    even_odd = config.get('schedule_even_odd', 'both')
    
    print(f"📅 Дни недели: {schedule_days}")
    print(f"🕐 Часы отправки: {schedule_hours}")
    print(f"🔢 Четность: {even_odd}")
    
    # Ищем следующий час сегодня
    next_send = None
    for hour in schedule_hours:
        if hour > now.hour and now.weekday() in schedule_days:
            next_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            # Проверка четности
            if even_odd == 'even' and next_time.day % 2 != 0:
                continue
            if even_odd == 'odd' and next_time.day % 2 == 0:
                continue
            next_send = next_time
            break
    
    # Ищем следующий день
    if not next_send:
        for day_offset in range(1, 15):
            next_day = now + timedelta(days=day_offset)
            if next_day.weekday() in schedule_days:
                for hour in schedule_hours:
                    next_time = next_day.replace(hour=hour, minute=0, second=0, microsecond=0)
                    # Проверка четности
                    if even_odd == 'even' and next_time.day % 2 != 0:
                        continue
                    if even_odd == 'odd' and next_time.day % 2 == 0:
                        continue
                    next_send = next_time
                    break
                if next_send:
                    break
    
    if next_send:
        time_diff = next_send - now
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        print(f"\n⏰ Следующая отправка:")
        print(f"   📅 Дата и время: {next_send.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   ⏳ Через: {hours} часов {minutes} минут")
        if hours > 24:
            days = hours // 24
            remaining_hours = hours % 24
            print(f"      ({days} дней {remaining_hours} часов)")
    else:
        print("\n❌ Не удалось определить следующее время отправки")
        
else:
    # Режим интервала
    interval = config.get('interval', 3600)
    interval_hours = interval // 3600
    
    print(f"⏱️  Интервал: {interval} секунд ({interval_hours} часов)")
    
    # Проверяем логи, чтобы найти время последней отправки
    log_file = '/opt/reklama_bot/bot.log'
    if not os.path.exists(log_file):
        log_file = 'bot.log'
    
    last_send_time = None
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if 'Отправлено для' in line:
                        # Ищем время в строке
                        import re
                        time_match = re.search(r'(\d{2}:\d{2} \d{2}\.\d{2}\.\d{4})', line)
                        if time_match:
                            try:
                                last_send_time = datetime.strptime(time_match.group(1), '%H:%M %d.%m.%Y')
                                break
                            except:
                                pass
        except:
            pass
    
    if last_send_time:
        next_send = last_send_time + timedelta(seconds=interval)
        time_diff = next_send - now
        
        if time_diff.total_seconds() > 0:
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            
            print(f"\n⏰ Следующая отправка:")
            print(f"   📅 Дата и время: {next_send.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   ⏳ Через: {hours} часов {minutes} минут")
            print(f"   📝 Последняя отправка была: {last_send_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"\n⚠️  Время следующей отправки уже прошло")
            print(f"   📝 Последняя отправка была: {last_send_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   ⚡ Бот должен отправить сообщение при следующей проверке")
    else:
        print(f"\n⚠️  Не удалось найти время последней отправки в логах")
        print(f"   💡 Бот отправит сообщение при следующем цикле (через {interval_hours} часов после запуска)")

print("\n" + "=" * 60)

