# 🚀 Автозапуск бота (работает независимо от SSH)

## Проблема: бот останавливается при закрытии терминала

Решение: настроить автозапуск через systemd service.

---

## ✅ Решение: Создать systemd service

### Шаг 1: Создать файл service

На сервере выполните:

```bash
nano /etc/systemd/system/reklama_bot.service
```

Вставьте следующее:

```ini
[Unit]
Description=Telegram Reklama Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/reklama_bot
ExecStart=/usr/bin/python3 /opt/reklama_bot/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Сохраните: **Ctrl+O**, **Enter**, **Ctrl+X**

---

### Шаг 2: Включить автозапуск

```bash
systemctl daemon-reload
systemctl enable reklama_bot
systemctl start reklama_bot
```

---

### Шаг 3: Проверить статус

```bash
systemctl status reklama_bot
```

Должно быть "active (running)".

---

## 🔧 Управление ботом:

### Запустить:
```bash
systemctl start reklama_bot
```

### Остановить:
```bash
systemctl stop reklama_bot
```

### Перезапустить:
```bash
systemctl restart reklama_bot
```

### Посмотреть логи:
```bash
journalctl -u reklama_bot -f
```

---

## ✅ Преимущества:

- ✅ Бот работает независимо от SSH
- ✅ Автоматически перезапускается при сбоях
- ✅ Автоматически запускается при перезагрузке сервера
- ✅ Удобное управление через systemctl
- ✅ Логи через journalctl

