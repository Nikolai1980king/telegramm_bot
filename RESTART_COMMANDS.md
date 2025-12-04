# 🔄 Команды для перезапуска бота

## Выполните на сервере по порядку:

```bash
cd /opt/reklama_bot

# 1. Остановить бот
pkill -9 -f "python3 main.py"

# 2. Подождать 2 секунды
sleep 2

# 3. Проверить, что процесс остановлен
ps aux | grep "python3 main.py" | grep -v grep

# 4. Перезапустить бот
nohup python3 main.py > bot.log 2>&1 &

# 5. Подождать 5 секунд
sleep 5

# 6. Проверить логи
tail -30 bot.log

# 7. Проверить процесс
ps aux | grep "python3 main.py" | grep -v grep
```

---

## ⚡ Или выполните всё одной командой:

```bash
cd /opt/reklama_bot && pkill -9 -f "python3 main.py" && sleep 2 && nohup python3 main.py > bot.log 2>&1 & sleep 5 && tail -30 bot.log
```

