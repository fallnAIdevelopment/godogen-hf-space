# Hugging Face Docker GPU Space for godogen + Babylon.js + local assets
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# System packages (no Ubuntu nodejs — it conflicts with Node 20)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    git curl wget unzip ca-certificates gnupg \
    xvfb ffmpeg imagemagick \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Node 20 from NodeSource (clean install, no old node packages)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && node --version && npm --version \
    && rm -rf /var/lib/apt/lists/*

# Python deps
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Pre-clone godogen + godogen_assets
RUN git clone --depth 1 https://github.com/htdt/godogen.git /opt/godogen \
    && git clone --depth 1 https://github.com/htdt/godogen_assets.git /opt/godogen_assets \
    && echo "/opt/godogen_assets" > /opt/godogen/.godogen_assets

# Workspace for published games
RUN mkdir -p /data/games /data/logs

COPY app.py /app/app.py
COPY agent.py /app/agent.py

EXPOSE 7860

CMD ["python3", "app.py"]
