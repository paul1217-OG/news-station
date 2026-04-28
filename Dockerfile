FROM python:3.11-slim

# 系統依賴：中文字型 + emoji 字型 + 時區
RUN apt-get update && apt-get install -y \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-noto-color-emoji \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway / Render 預設不持久化檔案，輸出存記憶體 / tmp 也 OK
RUN mkdir -p /app/output/cards

# 主入口：直接跑 main.py
CMD ["python", "src/main.py"]
