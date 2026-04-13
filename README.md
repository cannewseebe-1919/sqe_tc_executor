# SQE Test Executor

USB로 연결된 실제 Android 단말에서 테스트 케이스를 자동으로 실행하는 서버입니다.
sqe_tc_bot(TC Generator)에서 AI로 생성한 Python 테스트 코드를 받아 실행하고, 결과를 콜백으로 돌려줍니다.

**실행 환경**: Ubuntu 22.04 (ADB USB 접근을 위해 직접 설치 권장)

---

## 아키텍처

```
[sqe_tc_bot]
    ↓ POST /api/execute
[FastAPI Backend :8001]
    ↕                    ↕
[PostgreSQL] [Redis]    [ADB] ←→ [Android 단말]
    ↑                              ↕
콜백 결과 → sqe_tc_bot         [Runner App]
```

---

## 0단계: 사내망 환경 사전 설정

> **인터넷 차단 환경**이므로 아래 값을 사내 담당자에게 확인 후 기입하세요.

```
INTERNAL_DOCKER_REGISTRY = ______________   # 예: harbor.internal.company
INTERNAL_APT_MIRROR      = ______________   # 예: http://mirror.internal.company/ubuntu
INTERNAL_PIP_MIRROR      = ______________   # 예: http://pypi.internal.company/simple
INTERNAL_PIP_HOST        = ______________   # 예: pypi.internal.company
INTERNAL_NPM_REGISTRY    = ______________   # 예: http://npm.internal.company
```

### 호스트 apt 소스 설정 (Ubuntu 22.04)

```bash
sudo nano /etc/apt/sources.list
```

아래 내용으로 전체 교체:

```
deb http://mirror.internal.company/ubuntu jammy main restricted universe multiverse
deb http://mirror.internal.company/ubuntu jammy-updates main restricted universe multiverse
deb http://mirror.internal.company/ubuntu jammy-security main restricted universe multiverse
```

```bash
sudo apt-get update
```

### 호스트 pip 설정

```bash
mkdir -p ~/.config/pip
cat > ~/.config/pip/pip.conf << 'EOF'
[global]
index-url = http://pypi.internal.company/simple
trusted-host = pypi.internal.company
EOF
```

### 호스트 npm 설정 (프론트엔드 빌드 시)

```bash
npm config set registry http://npm.internal.company
```

### Docker 데몬에 사내 레지스트리 등록 (Docker Compose로 DB/Redis 실행 시)

```bash
sudo nano /etc/docker/daemon.json
```

```json
{
  "insecure-registries": ["harbor.internal.company"],
  "registry-mirrors": ["http://harbor.internal.company"]
}
```

```bash
sudo systemctl restart docker
```

---

## 1단계: 시스템 패키지 설치

```bash
sudo apt-get install -y \
    python3.12 python3.12-venv python3.12-dev \
    android-tools-adb \
    gcc libxml2-dev libxmlsec1-dev libxmlsec1-openssl pkg-config \
    git
```

### ADB 설치 확인

```bash
adb version
# Android Debug Bridge version 1.0.xx 가 나와야 함
```

### (선택) scrcpy 설치 — 화면 스트리밍 품질 향상

```bash
sudo apt-get install -y scrcpy
```

---

## 2단계: 프로젝트 다운로드

```bash
# 사내 git 서버에서 클론하는 경우
git clone http://git.internal.company/sqe/sqe_tc_executor.git
cd sqe_tc_executor
```

---

## 3단계: Python 가상환경 및 의존성 설치

```bash
cd backend

python3.12 -m venv venv
source venv/bin/activate

# pip 미러가 ~/.config/pip/pip.conf에 설정되어 있으면 그냥 실행
pip install -r requirements.txt

# 또는 미러를 직접 지정
pip install -r requirements.txt \
    --index-url http://pypi.internal.company/simple \
    --trusted-host pypi.internal.company
```

---

## 4단계: 환경변수 파일 작성

```bash
cp .env.example .env
nano .env
```

**반드시 수정해야 할 항목 (★):**

```env
# ★ JWT 시크릿 (sqe_tc_bot의 JWT_SECRET과 반드시 동일한 값)
JWT_SECRET=랜덤하고-강력한-시크릿값

# ★ CORS (sqe_tc_bot 프론트엔드 주소 포함)
CORS_ORIGINS=["http://tc-bot-서버-IP:3000","http://이-서버-IP:3001"]

# 직접 설치 시 localhost로 변경
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_executor
REDIS_URL=redis://localhost:6379/0

# SAML (개발·테스트 시 DEV_MODE=true 사용 가능)
DEV_MODE=false
```

> **개발/테스트 환경**: `DEV_MODE=true` 로 설정하면 SAML 없이 바로 사용 가능합니다.

---

## 5단계: PostgreSQL & Redis 실행

### 방법 A — Docker Compose (권장)

루트 `.env` 파일 생성:

```bash
cat > ../.env << 'EOF'
INTERNAL_REGISTRY=harbor.internal.company
APT_MIRROR=http://mirror.internal.company/ubuntu
PIP_INDEX_URL=http://pypi.internal.company/simple
PIP_TRUSTED_HOST=pypi.internal.company
NPM_REGISTRY=http://npm.internal.company
DB_PASSWORD=변경하세요
EOF
```

DB/Redis만 실행:

```bash
cd ..   # 프로젝트 루트로
docker compose up -d db redis
```

### 방법 B — 호스트에 직접 설치

```bash
# PostgreSQL
sudo apt-get install -y postgresql-16
sudo systemctl start postgresql
sudo -u postgres createdb test_executor

# Redis
sudo apt-get install -y redis-server
sudo systemctl start redis-server
```

---

## 6단계: DB 마이그레이션

```bash
cd backend
source venv/bin/activate

PYTHONPATH=. alembic upgrade head
```

---

## 7단계: 서버 실행

### 직접 실행 (개발/테스트)

```bash
cd backend
source venv/bin/activate

PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### systemd 서비스로 등록 (운영 환경 권장)

```bash
sudo nano /etc/systemd/system/sqe-tc-executor.service
```

```ini
[Unit]
Description=SQE TC Executor
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/sqe_tc_executor/backend
Environment=PYTHONPATH=/home/ubuntu/sqe_tc_executor/backend
ExecStart=/home/ubuntu/sqe_tc_executor/backend/venv/bin/uvicorn \
    app.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> `User`, `WorkingDirectory`, `ExecStart` 경로를 실제 경로로 변경하세요.

```bash
sudo systemctl daemon-reload
sudo systemctl enable sqe-tc-executor
sudo systemctl start sqe-tc-executor

# 상태 확인
sudo systemctl status sqe-tc-executor
```

---

## 8단계: Android 단말 설정

### USB 디버깅 활성화

1. Android 기기: **설정 → 휴대전화 정보 → 빌드번호** 7회 탭
2. **설정 → 개발자 옵션 → USB 디버깅** 활성화
3. USB 연결 후 기기의 "USB 디버깅 허용" 승인

### 연결 확인

```bash
adb devices
# 예시 출력:
# List of devices attached
# R3CR905XXXX    device
```

### Runner App 빌드 및 설치

> Runner App: UI 트리 탐색, 고품질 스크린샷, 화면 스트리밍을 담당하는 Android 앱

Runner App 빌드는 인터넷 없이 Gradle을 사용해야 합니다.

```bash
cd runner-app

# Gradle 의존성을 사내 Maven 미러에서 받도록 설정
# build.gradle의 repositories를 사내 Maven 미러로 변경 후 빌드
nano build.gradle
```

`build.gradle` 또는 `settings.gradle`의 `repositories` 블록을 수정:

```groovy
repositories {
    maven { url "http://maven.internal.company/repository/android-sdk/" }
    maven { url "http://maven.internal.company/repository/google/" }
    maven { url "http://maven.internal.company/repository/central/" }
}
```

```bash
./gradlew assembleDebug

# APK 설치
adb install app/build/outputs/apk/debug/app-debug.apk
```

### Runner App 권한 설정 (기기에서 수동)

1. **접근성 서비스**: 설정 → 접근성 → TestRunner → 활성화
2. **화면 오버레이**: 설정 → 앱 → TestRunner → 다른 앱 위에 표시 허용

---

## 9단계: 동작 확인

```bash
# 헬스체크
curl http://localhost:8001/health

# 단말 목록 (DEV_MODE=true)
curl http://localhost:8001/api/devices

# DEV_MODE=false인 경우 토큰 발급 후 사용
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/dev-login | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/devices
```

---

## (선택) 프론트엔드 실행

단말 목록 및 실행 현황을 웹으로 모니터링하려면 실행합니다.

```bash
cd frontend
npm config set registry http://npm.internal.company
npm install
npm run dev
# 또는 빌드 후 nginx로 서빙
npm run build
```

Docker Compose로 프론트엔드까지 실행:

```bash
# 루트 .env에 INTERNAL_REGISTRY, NPM_REGISTRY 설정 후
docker compose up -d frontend
```

프론트엔드: `http://이-서버-IP:3001`

---

## SAML SSO 설정 (운영 환경)

> DEV_MODE=true 사용 시 이 단계 건너뜀

```bash
nano backend/app/core/saml/settings.json
```

```json
{
  "sp": {
    "entityId": "http://이-서버-IP:8001/api/auth/saml/metadata",
    "assertionConsumerService": {
      "url": "http://이-서버-IP:8001/api/auth/saml/acs",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    },
    "singleLogoutService": {
      "url": "http://이-서버-IP:8001/api/auth/saml/slo",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    }
  },
  "idp": {
    "entityId": "http://idp.internal.company/saml/metadata",
    "singleSignOnService": {
      "url": "http://idp.internal.company/saml/sso",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "singleLogoutService": {
      "url": "http://idp.internal.company/saml/slo",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "x509cert": "사내 IdP의 X509 인증서를 여기에 붙여넣기"
  }
}
```

---

## 서비스 포트

| 서비스 | 포트 | 설명 |
|--------|------|------|
| 백엔드 API | 8001 | sqe_tc_bot에서 호출 |
| 프론트엔드 | 3001 | 모니터링 UI (선택) |
| PostgreSQL | 5433 | DB (Docker Compose 사용 시) |
| Redis | 6380 | 큐 (Docker Compose 사용 시) |

---

## 운영 명령어

```bash
# 서비스 상태 확인
sudo systemctl status sqe-tc-executor

# 서비스 재시작
sudo systemctl restart sqe-tc-executor

# 실시간 로그
sudo journalctl -u sqe-tc-executor -f

# DB 접속
psql -h localhost -U postgres -d test_executor

# 연결된 단말 확인
adb devices
```

---

## 환경변수 전체 목록

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `JWT_SECRET` | JWT 서명 키 (tc_bot과 동일) | **필수** |
| `DATABASE_URL` | PostgreSQL 접속 URL | **필수** |
| `REDIS_URL` | Redis 접속 URL | **필수** |
| `DEV_MODE` | `true`: SAML 우회 개발모드 | `false` |
| `ADB_PATH` | ADB 실행 파일 경로 | `adb` |
| `ADB_POLL_INTERVAL` | 단말 탐지 폴링 간격(초) | `5` |
| `RUNNER_APP_PORT` | Runner App HTTP 포트 | `8080` |
| `RUNNER_APP_APK_PATH` | APK 경로 | `runner-app/.../app-debug.apk` |
| `DEFAULT_STEP_TIMEOUT` | 스텝 타임아웃(초) | `30` |
| `SCREENSHOT_DIR` | 스크린샷 저장 경로 | `screenshots` |
| `LOG_DIR` | 로그 저장 경로 | `logs` |
| `LOGCAT_POLL_INTERVAL` | 크래시 감지 폴링(초) | `0.5` |
| `CORS_ORIGINS` | 허용 CORS 도메인 | **필수** |
| `DEBUG` | 디버그 로그 | `false` |

---

## 트러블슈팅

### ADB 단말이 인식되지 않음
```bash
adb kill-server
adb start-server
adb devices
```
→ USB 케이블 교체 시도, USB 디버깅 재활성화

### permission denied: adb
```bash
sudo usermod -aG plugdev $USER
# 재로그인 필요
```

### Runner App 통신 오류
```bash
# adb port forward 확인
adb forward tcp:8080 tcp:8080
```

### DB 마이그레이션 오류
```bash
source venv/bin/activate
PYTHONPATH=. alembic stamp head
PYTHONPATH=. alembic upgrade head
```

### pip 패키지 설치 실패
→ `~/.config/pip/pip.conf`의 `index-url` 확인
→ `trusted-host` 설정 여부 확인

### Docker 이미지 pull 실패
→ `/etc/docker/daemon.json`의 `insecure-registries` 확인
→ `sudo systemctl restart docker` 후 재시도

---

## 연동 서비스

- **sqe_tc_bot** — TC 코드 생성 및 실행 요청 (이 서버를 호출함)
- **사내 IdP** — SAML SSO 인증 (운영 시)

**중요**: `sqe_tc_bot`의 `JWT_SECRET`과 이 서버의 `JWT_SECRET`은 반드시 동일한 값이어야 합니다.
