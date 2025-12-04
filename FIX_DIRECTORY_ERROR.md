# 🔧 Исправление: файл не найден

## Проблема:
```
python3: can't open file '/root/main.py': [Errno 2] No such file or directory
```

Вы были в директории `/root`, а файл находится в `/opt/reklama_bot`

## ✅ Решение:

**ВСЕГДА** переходите в папку бота перед выполнением команд:

```bash
cd /opt/reklama_bot
```

---

## 📋 Правильная последовательность:

```bash
# 1. Перейти в папку бота
cd /opt/reklama_bot

# 2. Проверить, что файлы на месте
ls -la main.py templates/index.html

# 3. Проверить синтаксис
python3 -m py_compile main.py

# 4. Перезапустить бот
pkill -9 -f "python3 main.py"
sleep 2
nohup python3 main.py > bot.log 2>&1 &

# 5. Проверить логи
sleep 5
tail -30 bot.log
```

---

## ⚡ Или всё одной командой:

```bash
cd /opt/reklama_bot && ls -la main.py && python3 -m py_compile main.py && pkill -9 -f "python3 main.py" && sleep 2 && nohup python3 main.py > bot.log 2>&1 & sleep 5 && tail -30 bot.log
```

