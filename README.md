# SQE Test Executor

USB로 연결된 실제 Android 단말에서 테스트 케이스를 자동으로 실행하는 서버입니다.
sqe_tc_bot(TC Generator)에서 AI로 생성한 Python 테스트 코드를 받아 실행하고, 결과를 콜백으로 돌려줍니다.

**실행 환경**: Ubuntu 22.04 — Python 백엔드는 호스트에 직접 설치 (ADB USB 접근 필요), DB/Redis는 Docker Compose 사용

---

## 아키텍처

```
[sqe_tc_bot]
    ↓ POST /api/execute
[FastAPI Backend :8001]  ← 호스트에 직접 설치
    ↕                    ↕
[PostgreSQL] [Redis]    [ADB] ←→ [Android 단말]
(Docker)  (Docker)               ↕
    ↑                         [Runner App]
콜백 결과 → sqe_tc_bot
```

---

## 설정 파일 전체 요약

> 시작 전에 아래 표를 보고 어느 파일을 어디서 수정해야 하는지 파악하세요.

| 설정 항목 | 수정할 파일 | 위치 | 언제 |
|-----------|------------|------|------|
| Ubuntu apt 미러 | `/etc/apt/sources.list` | **서버 호스트** | 최초 1회 |
| pip 미러 | `~/.config/pip/pip.conf` | **서버 호스트** (실행 계정 홈) | 최초 1회 |
| Docker 사내 레지스트리 | `/etc/docker/daemon.json` | **서버 호스트** | 최초 1회 (DB/Redis Docker 사용 시) |
| Docker 빌드용 미러 | `프로젝트 루트/.env` | **서버 호스트** (프로젝트 폴더 내) | 최초 1회 |
| 앱 환경변수 (JWT 등) | `backend/.env` | **서버 호스트** (프로젝트 폴더 내) | 최초 1회 |
| SAML IdP 정보 | `backend/app/core/saml/settings.json` | **서버 호스트** (프로젝트 폴더 내) | 운영 환경만 |

> **Python 백엔드는 호스트에 직접 설치하므로** apt, pip 설정을 호스트에서 해야 합니다.
> DB/Redis는 Docker로 실행하므로 Docker 레지스트리 설정도 필요합니다.

---

## 사전 준비: 사내 인프라 주소 확인

아래 값을 사내 담당자에게 확인하세요. 이후 단계에서 사용합니다.

```
Docker 레지스트리 주소 : ___________________________  (예: harbor.company.internal)
apt 미러 URL          : ___________________________  (예: http://apt-mirror.company.internal/ubuntu)
PyPI 미러 URL         : ___________________________  (예: http://pypi-mirror.company.internal/simple)
PyPI 미러 호스트명     : ___________________________  (예: pypi-mirror.company.internal)
npm 레지스트리 URL     : ___________________________  (예: http://npm-registry.company.internal) ← 프론트엔드 빌드 시만 필요
sqe_tc_bot 서버 IP    : ___________________________  (TC Bot이 동작하는 서버 IP)
이 서버 IP            : ___________________________  (이 executor 서버의 IP)
```

---

## 0단계: 호스트 apt 미러 설정

**작업 위치**: 서버 호스트 터미널  
**파일 위치**: `/etc/apt/sources.list`  
**목적**: `apt-get install`로 패키지를 사내 미러에서 받기 위해 설정합니다.

```bash
sudo nano /etc/apt/sources.list
```

기존 내용을 모두 지우고 아래 내용으로 교체합니다 (실제 apt 미러 URL로 변경):

```
deb http://apt-mirror.company.internal/ubuntu jammy main restricted universe multiverse
deb http://apt-mirror.company.internal/ubuntu jammy-updates main restricted universe multiverse
deb http://apt-mirror.company.internal/ubuntu jammy-security main restricted universe multiverse
```

저장 후 패키지 목록 갱신:

```bash
sudo apt-get update
```

---

## 0단계: 호스트 pip 미러 설정

**작업 위치**: 서버 호스트 터미널  
**파일 위치**: `~/.config/pip/pip.conf` (현재 로그인한 계정의 홈 디렉토리)  
**목적**: `pip install`로 Python 패키지를 사내 미러에서 받기 위해 설정합니다.

```bash
mkdir -p ~/.config/pip
nano ~/.config/pip/pip.conf
```

아래 내용을 입력합니다 (실제 PyPI 미러 URL로 변경):

```ini
[global]
index-url = http://pypi-mirror.company.internal/simple
trusted-host = pypi-mirror.company.internal
```

---

## 0단계: Docker 사내 레지스트리 등록

**작업 위치**: 서버 호스트 터미널  
**파일 위치**: `/etc/docker/daemon.json`  
**목적**: Docker가 사내 레지스트리에서 PostgreSQL, Redis 이미지를 받기 위해 설정합니다.

```bash
sudo nano /etc/docker/daemon.json
```

아래 내용을 입력합니다 (실제 레지스트리 주소로 변경):

```json
{
  "insecure-registries": ["harbor.company.internal"],
  "registry-mirrors": ["http://harbor.company.internal"]
}
```

저장 후 Docker 재시작:

```bash
sudo systemctl restart docker
```

---

## 1단계: 시스템 패키지 설치

**작업 위치**: 서버 호스트 터미널

0단계에서 apt 미러 설정 후 실행합니다:

```bash
sudo apt-get install -y \
    python3.12 python3.12-venv python3.12-dev \
    android-tools-adb \
    gcc libxml2-dev libxmlsec1-dev libxmlsec1-openssl pkg-config \
    git
```

ADB 설치 확인:

```bash
adb version
# Android Debug Bridge version 1.0.xx 가 나와야 합니다
```

(선택) scrcpy 설치 — 화면 스트리밍 품질 향상:

```bash
sudo apt-get install -y scrcpy
```

---

## 2단계: 프로젝트 다운로드

**작업 위치**: 서버 호스트 터미널

```bash
git clone http://git.company.internal/sqe/sqe_tc_executor.git
cd sqe_tc_executor
```

인터넷이 완전히 차단된 경우 USB 등으로 파일을 옮긴 뒤 압축 해제하여 사용합니다.

---

## 3단계: Python 가상환경 및 의존성 설치

**작업 위치**: 서버 호스트 터미널  
**목적**: Python 백엔드를 호스트에 직접 설치합니다.

0단계에서 `~/.config/pip/pip.conf` 설정이 완료된 상태에서 실행합니다:

```bash
cd backend

python3.12 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

설치 중 패키지를 찾지 못하는 오류가 나면 pip.conf 설정을 확인하거나 직접 지정합니다:

```bash
pip install -r requirements.txt \
    --index-url http://pypi-mirror.company.internal/simple \
    --trusted-host pypi-mirror.company.internal
```

---

## 4단계: 루트 `.env` 작성 — Docker 빌드 설정

**작업 위치**: 서버 호스트 터미널  
**파일 위치**: `sqe_tc_executor/.env` (프로젝트 최상단)  
**목적**: DB/Redis Docker 컨테이너 빌드 시 사내 레지스트리 주소를 주입합니다.

```bash
# sqe_tc_executor/ 디렉토리에서 실행
nano .env
```

아래 내용을 입력합니다 (실제 주소로 변경):

```env
# ─── Docker 이미지 사내 레지스트리 ───────────────────────────────
INTERNAL_REGISTRY=harbor.company.internal
APT_MIRROR=http://apt-mirror.company.internal/ubuntu
PIP_INDEX_URL=http://pypi-mirror.company.internal/simple
PIP_TRUSTED_HOST=pypi-mirror.company.internal
NPM_REGISTRY=http://npm-registry.company.internal

# ─── DB 비밀번호 ─────────────────────────────────────────────────
DB_PASSWORD=강력한비밀번호로변경
```

---

## 5단계: `backend/.env` 작성 — 앱 설정

**작업 위치**: 서버 호스트 터미널  
**파일 위치**: `sqe_tc_executor/backend/.env`

```bash
# sqe_tc_executor/ 디렉토리에서 실행
cp backend/.env.example backend/.env
nano backend/.env
```

★ 표시된 항목을 반드시 실제 값으로 변경하세요:

```env
# ─── 앱 기본 설정 ────────────────────────────────────────────────
APP_NAME=Test Executor
DEBUG=false
HOST=0.0.0.0
PORT=8000
# 개발/테스트 시 true로 설정하면 SAML 없이 바로 사용 가능
DEV_MODE=false

# ─── 데이터베이스 ────────────────────────────────────────────────
# DB를 Docker Compose로 실행하면 localhost:5433 사용
# (docker-compose.yml에서 호스트 포트 5433으로 매핑)
DATABASE_URL=postgresql+asyncpg://postgres:강력한비밀번호로변경@localhost:5433/test_executor  # ★

# ─── Redis ───────────────────────────────────────────────────────
# Redis를 Docker Compose로 실행하면 localhost:6380 사용
REDIS_URL=redis://localhost:6380/0

# ─── JWT (sqe_tc_bot의 JWT_SECRET과 반드시 동일) ─────────────────
JWT_SECRET=랜덤하고-강력한-시크릿값-여기-입력          # ★
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ─── ADB 설정 ────────────────────────────────────────────────────
ADB_PATH=adb
ADB_POLL_INTERVAL=5
RUNNER_APP_PORT=8080
RUNNER_APP_APK_PATH=runner-app/prebuilt/app-debug.apk
SCRCPY_PATH=scrcpy

# ─── 실행 설정 ───────────────────────────────────────────────────
DEFAULT_STEP_TIMEOUT=30
SCREENSHOT_DIR=screenshots
LOG_DIR=logs
LOGCAT_POLL_INTERVAL=0.5

# ─── SAML SSO (DEV_MODE=false 운영 환경에서만 필요) ──────────────
SAML_SETTINGS_PATH=app/core/saml

# ─── CORS ────────────────────────────────────────────────────────
# sqe_tc_bot 프론트엔드 주소와 이 서버 프론트엔드 주소를 포함
CORS_ORIGINS=["http://tc-bot-서버-IP:3000","http://이-서버-IP:3001"]  # ★
```

> **DATABASE_URL의 비밀번호**는 루트 `.env`의 `DB_PASSWORD`와 동일하게 맞추세요.

---

## 6단계: DB/Redis 실행 (Docker Compose)

**작업 위치**: 서버 호스트 터미널 (`sqe_tc_executor/` 디렉토리)

```bash
docker compose up -d db redis
```

DB/Redis 실행 확인:

```bash
docker compose ps
# db, redis 모두 "Up" 상태인지 확인
```

---

## 7단계: DB 마이그레이션

**작업 위치**: 서버 호스트 터미널

```bash
cd backend
source venv/bin/activate

PYTHONPATH=. alembic upgrade head
```

---

## 8단계: 서버 실행

### 테스트 실행 (동작 확인용)

```bash
cd backend
source venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8001
```

헬스체크:

```bash
curl http://localhost:8001/health
# {"status":"ok"} 가 나오면 정상
```

### 운영 환경: systemd 서비스 등록

**작업 위치**: 서버 호스트 터미널  
**파일 위치**: `/etc/systemd/system/sqe-tc-executor.service`

서버 재부팅 시 자동 시작되도록 systemd 서비스로 등록합니다:

```bash
sudo nano /etc/systemd/system/sqe-tc-executor.service
```

아래 내용을 입력합니다 (`ubuntu` 부분은 실제 실행 계정명으로, 경로는 실제 경로로 변경):

```ini
[Unit]
Description=SQE TC Executor
After=network.target

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

```bash
sudo systemctl daemon-reload
sudo systemctl enable sqe-tc-executor
sudo systemctl start sqe-tc-executor

# 상태 확인
sudo systemctl status sqe-tc-executor
```

---

## 9단계: SAML 설정 (운영 환경만)

> `DEV_MODE=true` 사용 시 이 단계를 건너뜁니다.

**작업 위치**: 서버 호스트 터미널  
**파일 위치**: `sqe_tc_executor/backend/app/core/saml/settings.json`

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
    "entityId": "http://idp.company.internal/saml/metadata",
    "singleSignOnService": {
      "url": "http://idp.company.internal/saml/sso",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "singleLogoutService": {
      "url": "http://idp.company.internal/saml/slo",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "x509cert": "사내 IdP 담당자에게 X509 인증서 문자열을 받아 여기에 붙여넣기"
  }
}
```

---

## 10단계: Android 단말 설정

### USB 디버깅 활성화

1. Android 기기: **설정 → 휴대전화 정보 → 빌드번호** 7회 탭
2. **설정 → 개발자 옵션 → USB 디버깅** 활성화
3. USB 연결 후 기기의 "USB 디버깅 허용" 대화상자 승인

연결 확인:

```bash
adb devices
# 예시:
# List of devices attached
# R3CR905XXXX    device
```

### Runner App 설치

Runner App은 UI 트리 탐색, 고품질 스크린샷, 화면 스트리밍을 담당하는 Android 앱입니다.

사내망에서 Gradle 빌드가 불가하므로 미리 빌드된 APK를 사용합니다.

```bash
# 프로젝트 루트에서 실행
adb install runner-app/prebuilt/app-debug.apk
```

> APK를 새로 빌드해야 할 경우 외부망 PC에서 아래 명령어를 실행한 뒤
> `runner-app/prebuilt/app-debug.apk`를 교체하고 다시 커밋하세요.
> ```bash
> cd runner-app
> ANDROID_HOME=<Android SDK 경로> bash gradlew assembleDebug
> cp app/build/outputs/apk/debug/app-debug.apk prebuilt/app-debug.apk
> ```

### Runner App 권한 설정 (기기에서 수동)

1. **접근성 서비스**: 설정 → 접근성 → TestRunner → 활성화
2. **화면 오버레이**: 설정 → 앱 → TestRunner → 다른 앱 위에 표시 허용

---

## (선택) 프론트엔드 실행

단말 목록 및 실행 현황을 웹으로 모니터링하려면 실행합니다.

**직접 빌드 및 실행:**

```bash
cd frontend
npm config set registry http://npm-registry.company.internal   # 호스트 npm 미러 설정
npm install
npm run dev    # 개발 서버 (포트 3001)
```

**Docker Compose로 실행:**

```bash
# 루트 .env에 INTERNAL_REGISTRY, NPM_REGISTRY 설정 후
docker compose up -d frontend
```

프론트엔드: `http://이-서버-IP:3001`

---

## 서비스 포트

| 서비스 | 포트 | 실행 방식 | 설명 |
|--------|------|-----------|------|
| 백엔드 API | **8001** | 호스트 직접 실행 | sqe_tc_bot에서 호출 |
| 프론트엔드 | 3001 | 선택 사항 | 모니터링 UI |
| PostgreSQL | 5433 | Docker | DB |
| Redis | 6380 | Docker | 큐 |

---

## 운영 명령어

```bash
# 서비스 상태 확인
sudo systemctl status sqe-tc-executor

# 서비스 재시작
sudo systemctl restart sqe-tc-executor

# 실시간 로그
sudo journalctl -u sqe-tc-executor -f

# DB/Redis 재시작
docker compose restart db redis

# DB 직접 접속
docker compose exec db psql -U postgres -d test_executor

# 연결된 단말 확인
adb devices
```

---

## 환경변수 전체 목록

### `backend/.env`

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `JWT_SECRET` | JWT 서명 키 (tc_bot과 동일) | ★ |
| `DATABASE_URL` | PostgreSQL 접속 URL | ★ |
| `REDIS_URL` | Redis 접속 URL | ★ |
| `CORS_ORIGINS` | 허용 CORS 도메인 | ★ |
| `DEV_MODE` | `true`: SAML 우회 개발모드 | 기본값: `false` |
| `ADB_PATH` | ADB 실행 파일 경로 | 기본값: `adb` |
| `ADB_POLL_INTERVAL` | 단말 탐지 폴링 간격(초) | 기본값: `5` |
| `RUNNER_APP_PORT` | Runner App HTTP 포트 | 기본값: `8080` |
| `DEFAULT_STEP_TIMEOUT` | 스텝 타임아웃(초) | 기본값: `30` |
| `SCREENSHOT_DIR` | 스크린샷 저장 경로 | 기본값: `screenshots` |
| `LOG_DIR` | 로그 저장 경로 | 기본값: `logs` |

---

## 트러블슈팅

### apt-get install 실패
```
Unable to locate package
```
→ `/etc/apt/sources.list`의 apt 미러 URL 확인 후 `sudo apt-get update` 재실행

### pip install 실패
```
Could not find a version that satisfies the requirement
```
→ `~/.config/pip/pip.conf`의 `index-url`, `trusted-host` 확인

### Docker 이미지 pull 실패
→ `/etc/docker/daemon.json`의 `insecure-registries` 확인 후 `sudo systemctl restart docker`

### ADB 단말이 인식되지 않음
```bash
adb kill-server && adb start-server && adb devices
```
→ USB 케이블 교체, USB 디버깅 재활성화

### permission denied (adb)
```bash
sudo usermod -aG plugdev $USER
# 재로그인 필요
```

### DB 연결 오류
→ `backend/.env`의 `DATABASE_URL` 포트가 `5433`인지 확인 (Docker 매핑)
→ `docker compose ps`로 db 컨테이너가 실행 중인지 확인

### DB 마이그레이션 오류
```bash
source venv/bin/activate
PYTHONPATH=. alembic stamp head
PYTHONPATH=. alembic upgrade head
```

---

## 연동 서비스

- **sqe_tc_bot** — TC 코드 생성 및 실행 요청 (이 서버를 호출함)
- **사내 IdP** — SAML SSO 인증 (운영 시)

**중요**: `sqe_tc_bot`의 `JWT_SECRET`과 이 서버의 `JWT_SECRET`은 반드시 동일한 값이어야 합니다.
