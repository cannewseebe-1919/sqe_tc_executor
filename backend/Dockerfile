# -----------------------------------------------
# 사내망 환경 변수 (docker-compose.yml의 args 또는 --build-arg 로 주입)
# -----------------------------------------------
ARG INTERNAL_REGISTRY=docker-registry.internal
ARG APT_MIRROR=http://apt-mirror.internal/ubuntu
ARG PIP_INDEX_URL=http://pypi-mirror.internal/simple
ARG PIP_TRUSTED_HOST=pypi-mirror.internal

FROM ${INTERNAL_REGISTRY}/python:3.12-slim

# apt 미러를 사내 미러로 교체
ARG APT_MIRROR
RUN printf "deb %s jammy main restricted universe multiverse\n\
deb %s jammy-updates main restricted universe multiverse\n\
deb %s jammy-security main restricted universe multiverse\n" \
    "${APT_MIRROR}" "${APT_MIRROR}" "${APT_MIRROR}" \
    > /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxmlsec1-dev libxmlsec1-openssl pkg-config \
    android-tools-adb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pip 미러를 사내 미러로 교체
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --index-url "${PIP_INDEX_URL}" \
    --trusted-host "${PIP_TRUSTED_HOST}" \
    -r requirements.txt

COPY . .

RUN mkdir -p screenshots logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
