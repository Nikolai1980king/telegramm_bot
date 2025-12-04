# 🔧 Исправление конфига на сервере

## Проблемы в конфиге:

1. **Путь к изображению:** `/home/nikolai/PycharmProjects/telegramm_bot/image/cart_1.png` - это локальный путь!
   - На сервере файл называется `arduino_nano_pins.jpg`
   - Правильный путь: `image/arduino_nano_pins.jpg` (относительный)

2. **Путь к session файлу:** `/home/nikolai/PycharmProjects/telegramm_bot/session_name` - это локальный путь!
   - На сервере файл: `/opt/reklama_bot/session_name.session`
   - Правильный путь: `session_name` (относительный)

---

## Исправление на сервере:

### Вариант 1: Отредактировать через nano

```bash
cd /opt/reklama_bot
nano bot_config.json
```

Измените:
- `"photo_path": "image/arduino_nano_pins.jpg"` (или `"image/cart_1.png"` если загрузите правильный файл)
- `"session_file": "session_name"`

Сохраните: **Ctrl+O**, **Enter**, **Ctrl+X**

### Вариант 2: Через sed (быстро)

```bash
cd /opt/reklama_bot

# Исправить путь к изображению
sed -i 's|"photo_path": "/home/nikolai/PycharmProjects/telegramm_bot/image/cart_1.png"|"photo_path": "image/arduino_nano_pins.jpg"|g' bot_config.json

# Исправить путь к session файлу
sed -i 's|"session_file": "/home/nikolai/PycharmProjects/telegramm_bot/session_name"|"session_file": "session_name"|g' bot_config.json
```

### Вариант 3: Перезаписать конфиг

```bash
cd /opt/reklama_bot
cat > bot_config.json << 'EOF'
{
    "api_id": "27375139",
    "api_hash": "66e1bc627b8dda02e2bb35ea44fde4cf",
    "phone_number": "+79140024032",
    "recipients": [
        "@Nikolai198019"
    ],
    "interval": 32400,
    "photo_path": "image/arduino_nano_pins.jpg",
    "caption": "здесь будет видеоролик -переходи в приложение @znakomstva_v_kafe_bot",
    "is_running": false,
    "session_file": "session_name"
}
EOF
```

---

## После исправления:

1. **Проверить конфиг:**
   ```bash
   cat bot_config.json
   ```

2. **Перезапустить бота:**
   ```bash
   # Остановить старые процессы
   pkill -f "python3 main.py"
   
   # Запустить заново
   screen -S reklama_bot
   cd /opt/reklama_bot
   python3 main.py
   # Ctrl+A, затем D
   ```

3. **Проверить работу:**
   - Откройте веб-интерфейс
   - Нажмите "Запустить бота"
   - Проверьте логи в screen сессии


