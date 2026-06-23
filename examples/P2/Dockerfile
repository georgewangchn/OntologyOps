FROM swipl:latest

LABEL maintainer="森林瀑布"
LABEL description="P2 · 宠物疾病诊断推理（Prolog + FastAPI）"

ENV LANG=C.UTF-8

# 安装 Python 3（swipl 镜像基于 Debian，apt 装即可，无需从源码编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /requirements.txt

COPY src/ /app/src/
COPY data/ /app/data/

WORKDIR /app
ENV PYTHONPATH=/app:/app/src
EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
