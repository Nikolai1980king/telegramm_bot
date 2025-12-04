# ⚡ Быстрое исправление

## На сервере выполните:

### 1. Изменить порт на 5001:

```bash
cd /opt/reklama_bot
sed -i "s/port=5000/port=5001/g" main.py
```

### 2. Проверить:

```bash
grep "port=" main.py
```

Должно быть: `port=5001`

### 3. Загрузить обновленные файлы:

Через файловый менеджер Beget загрузите:
- `main.py` (с новыми функциями расписания)
- `templates/index.html` (с новым интерфейсом)

### 4. Запустить бота:

```bash
cd /opt/reklama_bot
screen -S reklama_bot
python3 main.py
```

Затем **Ctrl+A**, затем **D**.

---

## Или через SCP (с локального компьютера):

В новом терминале на локальном компьютере:

```bash
cd ~/PycharmProjects/telegramm_bot
scp main.py root@212.67.11.50:/opt/reklama_bot/
scp templates/index.html root@212.67.11.50:/opt/reklama_bot/templates/
```

Затем на сервере запустите бота.


