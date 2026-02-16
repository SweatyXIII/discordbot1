FROM python:3.10-slim

# Устанавливаем шрифты для русского языка
RUN apt-get update && apt-get install -y \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Важно: Render будет использовать CMD для запуска
CMD ["python", "bot.py"]
