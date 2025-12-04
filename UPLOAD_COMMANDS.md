# 📤 Команды для загрузки файлов на сервер

## Выполните на вашем локальном компьютере:

### 1. Загрузить main.py:

```bash
cd ~/PycharmProjects/telegramm_bot
scp main.py root@212.67.11.50:/opt/reklama_bot/
```

### 2. Загрузить templates/index.html:

```bash
scp templates/index.html root@212.67.11.50:/opt/reklama_bot/templates/
```

---

## Или всё одной командой:

```bash
cd ~/PycharmProjects/telegramm_bot
scp main.py root@212.67.11.50:/opt/reklama_bot/ && scp templates/index.html root@212.67.11.50:/opt/reklama_bot/templates/
```

---

## После загрузки на сервере:

```bash
ssh root@212.67.11.50
cd /opt/reklama_bot

# Проверить синтаксис
python3 -m py_compile main.py && echo "✅ OK!" || echo "❌ Ошибка!"

# Перезапустить бот
pkill -9 -f "python3 main.py"
sleep 2
nohup python3 main.py > bot.log 2>&1 &

# Проверить
sleep 5
tail -30 bot.log
```

---

## Или всё одной командой на сервере:

```bash
cd /opt/reklama_bot && python3 -m py_compile main.py && pkill -9 -f "python3 main.py" && sleep 2 && nohup python3 main.py > bot.log 2>&1 & sleep 5 && tail -30 bot.log
```

