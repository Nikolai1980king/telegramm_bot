# 🚀 Запуск бота в фоне

## Проблема: бот не запущен

Нужно запустить бота в фоне, чтобы он работал постоянно.

---

## Вариант 1: Через screen (рекомендуется)

```bash
cd /opt/reklama_bot
screen -S reklama_bot
python3 main.py
```

Затем:
- Нажмите **Ctrl+A**, затем **D** (бот продолжит работать)

**Проверить:**
```bash
screen -ls
ps aux | grep "python3 main.py"
```

---

## Вариант 2: Через nohup

```bash
cd /opt/reklama_bot
nohup python3 main.py > bot.log 2>&1 &
```

**Проверить:**
```bash
ps aux | grep "python3 main.py"
tail -f /opt/reklama_bot/bot.log
```

---

## Вариант 3: Через systemd (для автозапуска)

Создайте файл `/etc/systemd/system/reklama_bot.service`:

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

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
systemctl daemon-reload
systemctl enable reklama_bot
systemctl start reklama_bot
systemctl status reklama_bot
```

---

## После запуска проверьте:

```bash
# Проверить процесс
ps aux | grep "python3 main.py"

# Проверить порт
netstat -tlnp | grep 5001

# Открыть в браузере
http://212.67.11.50:5001
```


