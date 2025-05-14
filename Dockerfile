FROM nvidia/cuda:12.1.1-runtime-ubuntu20.04

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.8 \
    python3-pip \
    python3.8-venv \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3.8 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# First install pip and setuptools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Gunicorn FIRST with dependencies
RUN pip install --no-cache-dir gunicorn==21.2.0

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch==2.2.1 --extra-index-url https://download.pytorch.org/whl/cu121

# Configure environment
ENV FLASK_APP=app.py \
    DEVICE=cuda \
    HF_HOME="/cache/huggingface"

# Create cache directory
RUN mkdir -p ${HF_HOME} && \
    chmod -R 777 /cache

# Copy application
COPY . .

EXPOSE 5000
CMD ["/opt/venv/bin/python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "app:app"]