# Universal Red Agent Arsenal - Project AURIX
FROM python:3.11-slim

# 1. Install Essential System Utilities (C-extensions, Network, Utils)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    iputils-ping \
    nmap \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Comprehensive Library Suite
# Categorized for AI validation workflows
RUN pip install --no-cache-dir \
    # --- Web & APIs ---
    requests \
    urllib3 \
    beautifulsoup4 \
    selenium \
    scapy \
    # --- Database Connectors (The big ones) ---
    pymysql \
    psycopg2-binary \
    pymongo \
    redis \
    sqlalchemy \
    # --- File Formats & Parsing ---
    PyYAML \
    lxml \
    defusedxml \
    pandas \
    # --- Security & Crypto ---
    cryptography \
    pycryptodome \
    jwt \
    # --- System & OS Analysis ---
    psutil \
    sh \
    # --- Mocking & Testing ---
    pytest \
    unittest-xml-reporting

# Set up the work environment
WORKDIR /src

# Disable Python buffering for real-time log capture in SandboxExecutor
ENV PYTHONUNBUFFERED=1
