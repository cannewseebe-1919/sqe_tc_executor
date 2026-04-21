# SQE Test Executor

USB로 연결된 실제 Android 단말에서 테스트 케이스를 자동으로 실행하는 서버입니다.
sqe_tc_bot(TC Generator)에서 AI로 생성한 Python 테스트 코드를 받아 실행하고, 결과를 콜백으로 돌려줍니다.

**실행 환경**: Ubuntu 22.04 — Python 백엔드는 호스트에 직접 설치 (ADB USB 접근 필요), DB/Redis는 Docker Compose 사용

---

## 아키텍처

### 구성 요소 한눈에 보기

```
┌─────────────────────────────────────────────────────────────────┐
│  sqe_tc_bot  (TC 생성 서버)                                      │
│  - AI가 테스트 코드(Python)를 생성                               │
│  - POST /api/execute 로 실행 요청                                │
│  - 테스트 완료 시 콜백으로 결과 수신                              │
└───────────────────┬─────────────────────────────────────────────┘
                    │  HTTP API (포트 8001)
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI 백엔드  (이 서버, 호스트 직접 실행)                      │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ DeviceMonitor│  │  Scheduler   │  │     TestRunner        │  │
│  │ (5초마다    │  │  (Redis 큐)  │  │  (TC 스크립트 실행)   │  │
│  │  adb devices│  │  단말별 FIFO │  │  Python 서브프로세스  │  │
│  │  폴링)      │  │              │  │                       │  │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬────────────┘  │
│         │                │                      │               │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────┐  ┌──────────┐   ┌────────────────────────────┐
│   PostgreSQL    │  │  Redis   │   │  ADB (USB 통신 도구)        │
│  - 단말 목록   │  │  - 실행  │   │  - 단말 탐지 / 상태 확인   │
│  - 실행 이력   │  │    대기열 │   │  - 탭/스와이프 명령 전송   │
│  - 스텝 결과   │  │          │   │  - 포트 포워딩 설정        │
│  (Docker)      │  │ (Docker) │   └─────────────┬──────────────┘
└─────────────────┘  └──────────┘                 │ USB 케이블
                                                   ▼
                                    ┌──────────────────────────┐
                                    │  Android 단말            │
                                    │  ┌─────────────────────┐ │
                                    │  │   Runner App        │ │
                                    │  │  - 접근성 서비스    │ │
                                    │  │    (UI 트리 탐색)   │ │
                                    │  │  - 화면 캡처 서비스 │ │
                                    │  │  - WebSocket 통신   │ │
                                    │  └─────────────────────┘ │
                                    └──────────────────────────┘
```

---

### 요청부터 결과까지 — 전체 흐름

아래는 sqe_tc_bot에서 테스트를 요청했을 때 내부적으로 무슨 일이 일어나는지를 순서대로 설명합니다.

---

#### ① 단말 자동 등록 (항상 백그라운드에서 동작)

서버가 켜져 있는 동안 **DeviceMonitor**가 5초마다 `adb devices` 명령을 실행합니다.  
USB로 연결된 단말이 감지되면 자동으로 DB에 등록하고, 뽑히면 OFFLINE으로 표시합니다.  
사람이 별도로 단말을 등록할 필요가 없습니다.

```
[서버 시작]
    → DeviceMonitor 백그라운드 동작 시작
    → 5초마다: adb devices 실행
    → 새 단말 감지 시: 모델명·Android버전·해상도 조회 → DB 저장
    → 기존 단말 뽑힘 감지 시: DB 상태 → OFFLINE 변경
```

---

#### ② 테스트 실행 요청 (sqe_tc_bot → 백엔드)

sqe_tc_bot이 AI로 테스트 코드를 생성한 뒤, 아래와 같은 형태로 백엔드에 요청을 보냅니다.

```
POST /api/execute
{
  "device_id": "R3CR905XXXX",      ← 실행할 단말 ID
  "test_code": "from device import...",  ← AI가 생성한 Python 테스트 코드
  "callback_url": "http://bot-server/callback",  ← 완료 후 결과 받을 주소
  "requested_by": "user@company.com"
}
```

백엔드는 요청을 받으면 즉시 응답합니다:
- 단말이 **비어 있으면** → 바로 실행 시작, `{"status": "RUNNING"}` 반환
- 단말이 **이미 테스트 중이면** → Redis 큐에 대기 등록, `{"status": "QUEUED", "queue_position": 2}` 반환

같은 단말에 여러 요청이 동시에 와도 순서대로(FIFO) 처리됩니다.

---

#### ③ TC 스크립트 실행 (백엔드 → 단말)

TestRunner가 실제로 테스트를 실행합니다. 내부 동작:

```
[TestRunner]
    1. TC 스크립트를 임시 파일로 저장
    2. 보안 검사: os.system, subprocess, eval 등 위험 코드 차단
    3. Python 서브프로세스로 TC 스크립트 실행 (최대 10분)
    4. 동시에 CrashDetector 가동 → 단말 logcat 모니터링 (앱 크래시 감지)
```

TC 스크립트(AI 생성 코드) 내부에서는 SDK 함수를 호출합니다:

```python
# TC 스크립트 예시
device.tap(540, 1200)            # → adb shell input tap 540 1200
device.get_ui_tree()             # → Runner App에 HTTP 요청 → 접근성 서비스
device.screenshot()              # → Runner App에 HTTP 요청 → 화면 캡처 서비스
device.assert_element("로그인")  # → 화면에 해당 텍스트가 있는지 확인
```

---

#### ④ ADB ↔ Runner App 통신

단말과의 통신은 **두 가지 경로**로 이루어집니다.

| 작업 | 경로 | 설명 |
|------|------|------|
| 탭, 스와이프, 텍스트 입력 | **ADB 직접** | `adb shell input tap x y` |
| 앱 설치 / 실행 | **ADB 직접** | `adb install`, `adb shell am start` |
| UI 트리 조회 | **Runner App** | 접근성 서비스를 통해 화면 구조 JSON 반환 |
| 스크린샷 | **Runner App** | 화면 캡처 서비스로 PNG 반환 |

Runner App과의 통신은 WebSocket을 이용합니다:

```
[단말 내 Runner App] → WebSocket 연결 (ws://서버IP:8001/ws/runner)
                           ↓
                    [백엔드 /ws/runner 엔드포인트]
                           ↓ 명령 전송 (get_ui_tree, screenshot 등)
                    [Runner App] → 접근성 서비스 / 화면 캡처 → 결과 반환
```

---

#### ⑤ 화면 실시간 스트리밍 (선택)

테스트가 실행되는 동안 프론트엔드(모니터링 UI)에서 단말 화면을 실시간으로 볼 수 있습니다.

```
[브라우저]
    → WebSocket 연결: ws://서버:8001/api/execute/{id}/stream
    → 백엔드가 Runner App에서 PNG 프레임을 받아 브라우저로 중계
    → 약 10 FPS로 단말 화면이 실시간 표시
```

---

#### ⑥ 결과 반환 (백엔드 → sqe_tc_bot)

테스트가 끝나면 백엔드가 콜백 URL로 결과를 전송합니다.

```
POST {callback_url}
{
  "execution_id": "...",
  "status": "COMPLETED",           ← COMPLETED / FAILED / ABORTED
  "total_duration_sec": 42.3,
  "summary": {
    "total_steps": 10,
    "passed": 9,
    "failed": 1
  },
  "steps": [
    { "name": "로그인 버튼 탭", "status": "PASSED", "duration_sec": 1.2 },
    { "name": "메인화면 진입 확인", "status": "FAILED", "error_type": "AssertionError" }
  ],
  "crash_logs": [],                ← 앱 크래시 발생 시 logcat 로그
  "device_info": { "model": "Galaxy S23", ... }
}
```

ABORTED가 되는 경우:
- 앱 크래시 감지 (CrashDetector)
- 10분 타임아웃 초과
- 보안 위반 코드 감지

---

#### 전체 타임라인 요약

```
0s      bot → POST /api/execute
0.1s    백엔드 → 실행 ID 발급, 즉시 응답
0.1s    TC 스크립트 보안 검사 통과
0.2s    Python 서브프로세스 시작 (TC 코드 실행)
        CrashDetector 가동 (logcat 모니터링)
~Ns     각 스텝: adb 명령 / Runner App HTTP 통신
        스텝 결과 stdout으로 출력 → DB 저장
완료    bot의 callback_url로 결과 POST
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
3. USB 케이블로 서버에 연결
4. 기기 화면에 "USB 디버깅 허용" 대화상자가 뜨면 **허용** 탭

연결 확인:

```bash
adb devices
# 예시:
# List of devices attached
# R3CR905XXXX    device
#
# "unauthorized" 가 나오면 기기 화면에서 허용 대화상자를 확인하세요.
# "offline" 이 나오면 케이블 재연결 후 adb kill-server && adb start-server 실행
```

---

### Runner App 최초 설치 및 시작 (1회)

Runner App은 UI 트리 탐색, 고품질 스크린샷, 화면 스트리밍을 담당하는 Android 앱입니다.

**1. APK 설치**

```bash
# 프로젝트 루트에서 실행 (DEVICE_SERIAL은 adb devices로 확인)
adb -s <DEVICE_SERIAL> install runner-app/prebuilt/app-debug.apk
# Success 메시지가 나와야 합니다.
# 이미 설치된 경우: adb -s <DEVICE_SERIAL> install -r runner-app/prebuilt/app-debug.apk
```

**2. 접근성 서비스 활성화** (기기에서 수동)

기기 화면에서 직접 조작합니다:

1. **설정 → 접근성** 메뉴 진입
2. 목록에서 **TestRunner** (또는 "Test Platform Runner") 선택
3. 스위치를 **켬** 으로 토글 → "허용" 확인
4. 설정 화면에서 나옵니다.

또는 서버에서 adb로 접근성 설정 화면을 바로 열 수 있습니다:

```bash
adb -s <DEVICE_SERIAL> shell am start -a android.settings.ACCESSIBILITY_SETTINGS
```

**3. 화면 오버레이 권한 허용** (기기에서 수동)

```bash
# adb로 권한 설정 화면 바로 열기
adb -s <DEVICE_SERIAL> shell am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION \
  -d package:com.testplatform.runner
```

기기에서 **"다른 앱 위에 표시 허용"** 을 켭니다.

**4. Runner App 실행 및 서버 연결**

기기에서 **TestRunner 앱 아이콘**을 탭하여 실행합니다:

1. 앱 상단에 **"Accessibility: ENABLED"** (초록색) 가 표시되는지 확인
   - 빨간색이면 2단계로 돌아가서 접근성 서비스를 다시 활성화합니다.
2. **Server URL** 입력란에 executor 백엔드 WebSocket 주소 입력:
   ```
   ws://localhost:8001/ws/runner
   ```
   > USB 연결 시 백엔드가 `adb reverse tcp:8001 tcp:8001`을 자동으로 설정하므로 `localhost`를 사용합니다.
3. **Connect** 버튼 탭
4. 기기 화면에 **"화면 캡처 시작"** 권한 대화상자 출현 → **"지금 시작"** 탭
5. 앱 상태가 **"Connected"** (초록색) 로 바뀌면 완료

---

### 재부팅 후 Runner App 재시작

> 커널 패닉, 배터리 방전, fastboot 진입 후 reboot 등 기기가 재부팅된 경우

**접근성 서비스는 재부팅 후 자동으로 복구**됩니다. 별도 설정 불필요.

**화면 캡처 권한(MediaProjection)은 Android 보안 정책에 의해 재부팅 시 초기화**되므로, 아래 절차로 재시작해야 합니다.

```bash
# 1. USB 재연결 후 기기 인식 확인
adb devices
# R3CR905XXXX    device  ← 이 상태여야 함
```

기기에서:
1. **TestRunner 앱** 실행
2. Server URL이 이전에 입력한 값으로 자동 채워져 있는지 확인 (저장됨)
3. **Connect** 버튼 탭
4. **"화면 캡처 시작"** 대화상자 → **"지금 시작"** 탭
5. **"Connected"** 확인 → 완료

> **자동화 불가 사유**: MediaProjection(화면 캡처) 권한은 Android OS가 매 세션마다 사용자 동의를 강제합니다. adb 명령이나 코드로 우회할 수 없는 보안 제약입니다. 접속 자체(Connect 탭)는 수동 1회 필수입니다.

**fastboot 모드에서 복구하는 경우:**

```bash
# fastboot 모드에서 정상 부팅
fastboot reboot

# 부팅 완료 확인 (30~60초 대기)
adb wait-for-device && adb devices

# 앱 실행 화면을 띄워두면 빠르게 Connect 가능
adb -s <DEVICE_SERIAL> shell am start -n com.testplatform.runner/.MainActivity
```

이후 기기 화면에서 **Connect → "지금 시작"** 탭합니다.

---

### Runner App APK 직접 빌드

`runner-app/prebuilt/app-debug.apk`에 사전 빌드된 APK가 포함되어 있어 바로 사용할 수 있습니다.
소스를 수정했거나 직접 빌드가 필요한 경우 아래 절차를 따릅니다.

**사전 준비**

- [Android Studio](https://developer.android.com/studio) 설치 (JDK 포함)
- 또는 JDK 17+ 단독 설치 + `ANDROID_HOME` 환경변수 설정

**빌드 명령**

```bash
cd runner-app

# Windows (Android Studio 기본 JRE 사용)
set JAVA_HOME=C:\Program Files\Android\Android Studio\jre
gradlew.bat assembleDebug

# Linux / macOS
JAVA_HOME=/path/to/jdk ./gradlew assembleDebug
```

**빌드 결과물 교체**

```bash
# Windows
copy app\build\outputs\apk\debug\app-debug.apk prebuilt\app-debug.apk

# Linux / macOS
cp app/build/outputs/apk/debug/app-debug.apk prebuilt/app-debug.apk
```

빌드 후 `prebuilt/app-debug.apk`를 커밋하면 다른 PC에서도 gradle 없이 바로 설치할 수 있습니다.

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

---

## 버전 히스토리

### v1.2 — 2026-04-21

#### 주요 변경 사항

**Runner App ↔ 백엔드 통신 방식 전면 개편**

기존에는 Runner App이 자체 HTTP 서버를 열고 백엔드가 ADB 포트 포워딩(`adb forward`)으로 접속하는 구조였습니다.  
v1.2부터는 Runner App이 WebSocket 클라이언트로 동작하여 백엔드의 `/ws/runner` 엔드포인트에 먼저 연결합니다.  
이로써 ADB 포트 포워딩이 필요 없어지고, USB 연결 즉시 단말이 자동으로 백엔드에 등록됩니다.

```
이전: 백엔드 --[adb forward tcp:9090]--> Runner App HTTP 서버
이후: Runner App --[WebSocket ws://localhost:8001/ws/runner]--> 백엔드
```

**adb reverse 자동 설정**

사내 Wi-Fi 환경에서 단말이 서버 IP로 직접 접근할 수 없는 경우를 위해,  
단말 연결(또는 재연결) 시 백엔드가 자동으로 `adb reverse tcp:8001 tcp:8001`을 실행합니다.  
이를 통해 Runner App은 `ws://localhost:8001/ws/runner`로 연결하면 됩니다.

#### 상세 변경 내역

| 분류 | 항목 | 설명 |
|------|------|------|
| **백엔드 신규** | `GET /api/executions` | 실행 이력 목록 조회 (device_id·status·limit·offset 필터 지원) |
| **백엔드 신규** | `GET /api/queues` | 장치별 현재 실행 중·대기 중 목록 조회 |
| **백엔드 신규** | `GET /api/auth/me` | JWT에서 사용자 정보(email·name·department) 반환 |
| **백엔드 신규** | `POST /api/auth/logout` | 로그아웃 처리 (stateless JWT, 200 OK 반환) |
| **백엔드 신규** | `GET /ws/runner` | Runner App WebSocket 연결 수신 엔드포인트 |
| **백엔드 신규** | `runner_registry.py` | WebSocket 연결 레지스트리 — android_id 기반 request/response 매칭 |
| **백엔드 수정** | `runner_app_client.py` | HTTP → WebSocket 명령 방식으로 전면 재작성 |
| **백엔드 수정** | `GET /api/execute/{id}/status` | 응답에 steps·summary·device_info·crash_logs 포함하도록 확장 |
| **백엔드 수정** | `GET /api/execute/{id}/result` | QUEUED/RUNNING 상태에서 400 에러 제거 → 현재 상태 그대로 반환 |
| **백엔드 수정** | `DeviceOut` 스키마 | `connected_at`, `last_seen_at` 필드 추가 |
| **백엔드 수정** | `StepResultOut` 스키마 | `name` → `step_name`, `step_order`·`execution_id` 필드 추가 |
| **백엔드 수정** | `device_monitor.py` | 단말 재연결 시 adb reverse 재설정 + 대기 큐 자동 처리 |
| **백엔드 수정** | `crash_detector.py` | logcat에 `-T 1` 추가 — 연결 이전 로그로 인한 오탐 방지 |
| **백엔드 수정** | `screen_streamer.py` | ADB 폴백 후 30초마다 Runner App 재연결 자동 시도 |
| **Runner App** | `ServerCommunicator.java` | `android_id` 기반 `device_id` 포함하여 device_info 메시지 전송 |
| **Runner App** | `prebuilt/app-debug.apk` | 위 변경 사항 반영하여 재빌드 |
| **README** | APK 빌드 가이드 추가 | 사내 Gradle 접근 가능 환경에서 직접 빌드하는 방법 |
| **README** | adb 명령어 `-s` 옵션 추가 | 다중 단말 환경에서 장치 지정 누락 수정 |

#### 마이그레이션 안내

Runner App 설정에서 서버 URL을 다음과 같이 변경해야 합니다:

| | 이전 (v1.1) | v1.2 |
|-|------------|------|
| Runner App 서버 URL | `ws://서버IP:8001/ws/runner` | `ws://localhost:8001/ws/runner` |
| ADB 설정 | `adb forward tcp:9090 tcp:9090` 수동 필요 | 백엔드 자동 설정 (`adb reverse`) |

> **참고**: `adb reverse`는 USB 연결 시 백엔드가 자동으로 실행합니다. 별도 수동 설정 불필요.

---

### v1.1 — 이전 버전

- Runner App HTTP 서버 + ADB 포트 포워딩 방식
- 기본 실행·스케줄링·크래시 감지 기능
- 사전 빌드 APK 배포 (`runner-app/prebuilt/app-debug.apk`)

**중요**: `sqe_tc_bot`의 `JWT_SECRET`과 이 서버의 `JWT_SECRET`은 반드시 동일한 값이어야 합니다.
