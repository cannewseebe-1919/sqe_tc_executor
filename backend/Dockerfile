FROM python:3.12-slim

WORKDIR /app

# System dependencies (for python3-saml / lxml)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libxml2-dev libxmlsec1-dev libxmlsec1-openssl pkg-config \
        android-tools-adb && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
