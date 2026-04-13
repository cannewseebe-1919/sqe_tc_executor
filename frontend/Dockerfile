# -----------------------------------------------
# 사내망 환경 변수
# -----------------------------------------------
ARG INTERNAL_REGISTRY=docker-registry.internal
ARG NPM_REGISTRY=http://npm-registry.internal

# ── 1단계: 빌드 ────────────────────────────────
FROM ${INTERNAL_REGISTRY}/node:18-alpine AS builder

ARG NPM_REGISTRY

WORKDIR /app

# npm 레지스트리를 사내 레지스트리로 교체
RUN npm config set registry ${NPM_REGISTRY}

COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

COPY . .
RUN npm run build

# ── 2단계: nginx 서빙 ──────────────────────────
FROM ${INTERNAL_REGISTRY}/nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80
