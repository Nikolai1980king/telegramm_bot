#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, '/opt/reklama_bot')

# Импортируем Flask приложение
from main import app

# Для работы через WSGI
application = app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


