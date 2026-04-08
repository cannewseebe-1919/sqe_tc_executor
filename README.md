# SQE Test Executor

Android 단말 테스트 자동 실행 서버입니다.
USB로 연결된 Android 디바이스를 관리하고, ADB + Runner App을 통해 테스트 케이스를 실행하며, 실시간 화면 스트리밍과 FIFO 스케줄링을 제공합니다.

[TC Generator (sqe_tc_bot)](https://github.com/cannewseebe-1919/sqe_tc_bot)에서 AI로 생성한 테스트 코드를 실제 Android 단말에서 실행하는 역할을 합니다.

---

## 아키텍처

```
[Browser] ←→ [React Frontend :3001] ←→ [FastAPI Backend :8001] ←→ [ADB] ←→ [Android Devices]
                                              ↕                        ↕
                                     [PostgreSQL] [Redis]       [Runner App]
                                              ↕                  (on device)
                                     [TC Generator :8000]
                                    (sqe_tc_bot / MCP 서버)
```

---

## 사전 요구사항

- **Python 3.12+**
- **PostgreSQL 16** (또는 Docker로 실행)
- **Redis 7** (또는 Docker로 실행)
- **ADB** (Android Debug Bridge) — Android SDK Platform-Tools
- **scrcpy** — 실시간 화면 스트리밍용 (선택 사항)
- **USB로 연결된 Android 디바이스** (USB 디버깅 활성화 필요)
- **Node.js 18+ & npm** (프론트엔드 실행 시)
- **Docker & Docker Compose** (DB/Redis를 컨테이너로 실행하는 경우)

---

## 로컬 실행 방법 (권장)

USB 디바이스에 직접 접근해야 하므로 로컬 실행을 권장합니다.

### 1. 저장소 클론

```bash
git clone https://github.com/cannewseebe-1919/sqe_tc_executor.git
cd sqe_tc_executor
```

### 2. 환경변수 설정

`backend/.env` 파일을 생성합니다.

```env
# 개발 모드 (DEV_MODE=true이면 SAML SSO 없이 API 사용 가능)
DEV_MODE=true
DEBUG=true

# JWT 시크릿 (sqe_tc_bot의 JWT_SECRET과 반드시 동일한 값 사용)
JWT_SECRET=dev-secret-change-in-production

# DB / Redis
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_executor
REDIS_URL=redis://localhost:6379/0

# ADB / scrcpy 경로
ADB_PATH=adb
SCRCPY_PATH=scrcpy

# CORS 허용 도메인
CORS_ORIGINS=["http://localhost:3001","http://localhost:3000"]
```

> **팁**: 이 저장소의 `backend/.env`에는 `DEV_MODE=true`와 개발용 JWT 시크릿이 예시값으로 포함되어 있습니다.
> 프로덕션 배포 전 반드시 `DEV_MODE=false`로 변경하고 강력한 `JWT_SECRET`을 사용하세요.

### 3. PostgreSQL & Redis 실행

Docker Compose로 DB와 Redis만 띄우는 방법:

```bash
docker compose up -d db redis
```

또는 로컬에 PostgreSQL/Redis가 이미 설치되어 있다면 직접 실행해도 됩니다.

### 4. Python 가상환경 설정 및 의존성 설치

```bash
cd backend

# 가상환경 생성 (최초 1회)
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 의존성 설치
pip install -r requirements.txt
```

> 이 저장소에는 이미 `backend/venv/`가 포함되어 있어 재생성 없이 바로 활성화해서 사용할 수 있습니다.

### 5. DB 마이그레이션

```bash
# backend/ 디렉토리에서 실행
PYTHONPATH=. alembic upgrade head
```

Windows에서 환경변수를 인라인으로 설정하기 어려운 경우:

```bash
# PowerShell
$env:PYTHONPATH="."; alembic upgrade head

# Git Bash / MINGW
PYTHONPATH=. alembic upgrade head
```

### 6. 서버 실행

```bash
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

서버 기동 확인:
- API 서버: http://localhost:8001
- 헬스체크: http://localhost:8001/health
- Swagger UI: http://localhost:8001/docs

### 7. 프론트엔드 실행 (선택)

```bash
cd frontend
npm install
npm run dev
```

프론트엔드: http://localhost:3001

---

## 개발 모드 (DEV_MODE)

사내 SAML SSO 환경이 갖춰지지 않은 상황에서도 API를 바로 사용할 수 있도록 개발 모드를 지원합니다.

### 설정

`backend/.env`에 다음을 추가합니다:

```env
DEV_MODE=true
```

### 개발용 JWT 토큰 발급

`DEV_MODE=true` 상태에서 아래 엔드포인트를 호출하면 인증 없이 JWT 토큰을 발급받을 수 있습니다:

```bash
curl -X POST http://localhost:8001/api/auth/dev-login
```

응답 예시:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

이후 API 호출 시 `Authorization: Bearer <token>` 헤더를 포함합니다:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8001/api/devices
```

> `DEV_MODE=false` (프로덕션)에서는 `/api/auth/dev-login` 호출 시 `403 Forbidden`이 반환됩니다.

---

## MCP 연동 (sqe_tc_bot)

[sqe_tc_bot](https://github.com/cannewseebe-1919/sqe_tc_bot)의 MCP 서버(`backend/mcp_server.py`)가 이 서버의 REST API를 직접 호출합니다.
AI가 테스트 케이스를 생성하고 → MCP 툴을 통해 이 서버에 실행 요청을 보내는 흐름입니다.

### MCP에서 사용하는 엔드포인트

| MCP 툴 이름 | HTTP 메서드 | 엔드포인트 | 설명 |
|------------|------------|-----------|------|
| `list_devices` | GET | `/api/devices` | 연결된 디바이스 목록 조회 |
| `execute_test` | POST | `/api/execute` | TC 실행 요청 |
| `get_execution_status` | GET | `/api/execute/{id}/status` | 실행 상태 조회 |
| `get_execution_result` | GET | `/api/execute/{id}/result` | 실행 결과 조회 |

### DEV_MODE에서의 MCP 연동

`DEV_MODE=true`로 설정하면 sqe_tc_bot의 MCP 서버가 JWT 토큰 없이 이 서버의 API를 호출할 수 있습니다.

sqe_tc_bot 쪽 MCP 설정(`backend/.env`)에서 이 서버의 주소를 지정합니다:

```env
# sqe_tc_bot의 .env
EXECUTOR_BASE_URL=http://localhost:8001
DEV_MODE=true
```

**중요**: 두 서비스의 `JWT_SECRET` 값은 반드시 동일하게 설정해야 합니다.

---

## TestCase SDK 작성 가이드

`app/sdk/`에 내장된 SDK를 활용해 테스트 케이스를 작성합니다.
sqe_tc_bot이 AI로 생성하는 코드도 이 SDK를 사용합니다.

### 임포트

```python
from app.sdk import TestCase, device, step, assert_screen, assert_element
```

### 기본 구조 예시

```python
from app.sdk import TestCase, device, step, assert_screen

class LoginTest(TestCase):
    app_package = "com.example.app"

    @step(name="launch_app")
    def step_01_launch(self):
        device.launch_app(self.app_package)
        device.wait(2)
        assert_screen(text_exists="Login")

    @step(name="verify_login")
    def step_02_verify(self):
        device.tap(text="Username")
        device.input_text("testuser")
        device.tap(text="Password")
        device.input_text("password123")
        device.tap(text="Sign In")
        assert_screen(text_exists="Welcome")

if __name__ == "__main__":
    LoginTest().run()
```

### `device` 객체 주요 메서드

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `device.launch_app(package)` | 앱 실행 | `device.launch_app("com.example.app")` |
| `device.stop_app(package)` | 앱 강제 종료 | `device.stop_app("com.example.app")` |
| `device.tap(text=, resource_id=, xy=)` | 요소 탭 | `device.tap(text="Login")` |
| `device.long_tap(text=, duration=)` | 요소 길게 탭 | `device.long_tap(text="Item", duration=1500)` |
| `device.swipe(start_xy, end_xy, duration=)` | 좌표 기반 스와이프 | `device.swipe((100,500),(100,200))` |
| `device.swipe_direction(direction)` | 방향 기반 스와이프 | `device.swipe_direction("up")` |
| `device.input_text(text)` | 텍스트 입력 | `device.input_text("hello")` |
| `device.press_key(key)` | 키 입력 | `device.press_key("back")` |
| `device.wait(seconds)` | 대기 | `device.wait(2)` |
| `device.find_element(text=, resource_id=)` | 요소 탐색 (Runner App) | `device.find_element(text="OK")` |
| `device.wait_for_element(text=, timeout=)` | 요소 대기 | `device.wait_for_element(text="OK", timeout=10)` |
| `device.element_exists(text=, resource_id=)` | 요소 존재 여부 확인 | `device.element_exists(text="Error")` |
| `device.screenshot(name=)` | 스크린샷 저장 | `device.screenshot("step01")` |
| `device.get_current_activity()` | 현재 Activity 확인 | `device.get_current_activity()` |
| `device.get_device_info()` | 디바이스 정보 조회 | `device.get_device_info()` |

`press_key` 지원 키 목록: `back`, `home`, `enter`, `menu`, `volume_up`, `volume_down`, `power`, `tab`, `delete`, `recent`

### `assert_screen` 사용법

현재 화면의 상태를 검증합니다. Runner App의 UI 트리를 기반으로 동작합니다.

```python
from app.sdk import assert_screen

# 텍스트가 화면에 존재하는지 확인
assert_screen(text_exists="Welcome")

# 텍스트가 화면에 없는지 확인
assert_screen(text_not_exists="Error")

# resource_id로 요소 존재 여부 확인
assert_screen(resource_id_exists="com.example.app:id/main_button")

# 여러 조건 동시 검증
assert_screen(text_exists="Home", text_not_exists="Login")
```

### `assert_element` 사용법

특정 요소의 속성값을 검증합니다.

```python
from app.sdk import assert_element

# 특정 요소의 text 속성 검증
assert_element(resource_id="com.example.app:id/title", attribute="text", expected="홈")

# 요소의 enabled 상태 검증
assert_element(text="Submit", attribute="enabled", expected="True")
```

---

## API 엔드포인트

### 인증

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | 헬스체크 |
| POST | `/api/auth/dev-login` | 개발 모드 JWT 토큰 발급 (`DEV_MODE=true` 전용) |
| GET | `/api/auth/saml/login` | SAML SSO 로그인 시작 |
| POST | `/api/auth/saml/acs` | SAML ACS 콜백 처리 |
| GET | `/api/auth/saml/metadata` | SP 메타데이터 (IdP 등록용) |

### 디바이스

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/devices` | 연결된 디바이스 목록 |
| GET | `/api/devices/{serial}` | 디바이스 상세 정보 |
| WS | `/api/devices/{id}/stream` | 디바이스 실시간 화면 스트리밍 |

### 실행

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/execute` | TC 실행 요청 (FIFO 큐 등록) |
| GET | `/api/execute/{id}/status` | 실행 상태 조회 |
| GET | `/api/execute/{id}/result` | 실행 결과 조회 |
| WS | `/api/execute/{id}/stream` | 실행 중 화면 스트리밍 |

---

## 환경변수 전체 목록

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `DEV_MODE` | 개발 모드 (true이면 SAML SSO 없이 API 사용 가능) | `false` |
| `DEBUG` | 디버그 로그 출력 | `false` |
| `DATABASE_URL` | PostgreSQL 접속 URL | `postgresql+asyncpg://postgres:postgres@localhost:5432/test_executor` |
| `REDIS_URL` | Redis 접속 URL | `redis://localhost:6379/0` |
| `ADB_PATH` | ADB 실행 파일 경로 | `adb` |
| `ADB_POLL_INTERVAL` | 디바이스 탐지 폴링 간격(초) | `5` |
| `RUNNER_APP_PORT` | Runner App 통신 포트 | `8080` |
| `RUNNER_APP_APK_PATH` | Runner App APK 경로 | `runner-app/app/build/outputs/apk/debug/app-debug.apk` |
| `SCRCPY_PATH` | scrcpy 실행 파일 경로 | `scrcpy` |
| `JWT_SECRET` | JWT 서명 시크릿 (sqe_tc_bot과 동일 값 사용) | `change-me-in-production` |
| `JWT_ALGORITHM` | JWT 알고리즘 | `HS256` |
| `JWT_EXPIRE_MINUTES` | JWT 만료 시간(분) | `60` |
| `DEFAULT_STEP_TIMEOUT` | TC 스텝 실행 타임아웃(초) | `30` |
| `SCREENSHOT_DIR` | 스크린샷 저장 디렉토리 | `screenshots` |
| `LOG_DIR` | 로그 저장 디렉토리 | `logs` |
| `LOGCAT_POLL_INTERVAL` | 크래시 감지 logcat 폴링(초) | `0.5` |
| `SAML_SETTINGS_PATH` | SAML 설정 파일 경로 | `app/core/saml/settings.json` |
| `CORS_ORIGINS` | 허용 CORS 도메인 | `["http://localhost:3000","http://localhost:3001"]` |

---

## 주요 기능

### FIFO 스케줄링

Redis 기반 디바이스별 큐를 사용합니다. 동일한 디바이스에 여러 실행 요청이 들어오면 FIFO 순서로 순차 실행됩니다.

### WebSocket 화면 스트리밍

실행 중인 디바이스 화면을 실시간으로 스트리밍합니다:
- `/api/execute/{id}/stream` — 특정 실행 세션 화면
- `/api/devices/{id}/stream` — 디바이스 직접 스트리밍

### 자동 크래시 감지

logcat을 실시간으로 모니터링하여 앱 크래시를 자동 감지하고 실행을 중단합니다.
ADB 연결이 끊어진 경우에도 자동으로 감지합니다.

---

## 프로젝트 구조

```
sqe_tc_executor/
├── backend/
│   ├── app/
│   │   ├── api/           # API 라우터 (auth, devices, execution, streaming)
│   │   ├── core/          # 설정, 인증, DB, SAML
│   │   │   └── saml/      # SAML IdP 설정 파일
│   │   ├── models/        # SQLAlchemy 모델 (Device, Execution, ExecutionStep)
│   │   ├── schemas/       # Pydantic 스키마
│   │   ├── sdk/           # TestCase SDK (TestCase, @step, device, assertions)
│   │   └── services/      # ADB, 디바이스 모니터, 스케줄러, 크래시 감지, 스트리밍
│   ├── alembic/           # DB 마이그레이션
│   ├── .env               # 환경변수 (DEV_MODE=true 포함)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/         # LoginPage, SamlCallbackPage
│   │   ├── components/    # DeviceList, DeviceStream, QueueStatus, ExecutionHistory
│   │   └── hooks/         # useWebSocket
│   └── package.json
├── runner-app/            # Android Runner App (Java, minSdk 21)
│   ├── app/
│   │   └── src/main/java/ # AccessibilityService, ScreenCapture, UITreeParser
│   ├── build.gradle
│   └── settings.gradle
└── docker-compose.yml
```

---

## 디바이스 설정 가이드

### USB 디버깅 활성화

1. Android 기기에서 **설정 → 휴대전화 정보 → 빌드번호** 7회 탭 → 개발자 옵션 활성화
2. **설정 → 개발자 옵션 → USB 디버깅** 활성화
3. USB 연결 후 기기에서 "USB 디버깅 허용" 대화상자 승인

디바이스 연결 확인:

```bash
adb devices
```

### Runner App 빌드 및 설치

Runner App은 디바이스에서 UI 트리 탐색, 스크린샷, 화면 스트리밍을 담당합니다.

```bash
cd runner-app
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

> Runner App 없이도 기본 ADB 명령 기반 테스트는 실행 가능합니다.
> 단, `device.find_element()`, `assert_screen()` 등 UI 트리 기반 기능은 Runner App이 필요합니다.

### Runner App 권한 설정

Runner App 설치 후 다음 권한을 수동으로 활성화해야 합니다:

1. **접근성 서비스**: 설정 → 접근성 → TestRunner → 활성화 (UI 트리 탐색용)
2. **화면 오버레이**: 설정 → 앱 → TestRunner → 다른 앱 위에 표시 허용 (스크린샷/스트리밍용)

---

## SAML SSO 설정 (프로덕션)

`DEV_MODE=false` 환경에서는 SAML 2.0 SSO 인증이 필요합니다.
`backend/app/core/saml/settings.json`에서 IdP 정보를 수정합니다:

```json
{
  "sp": {
    "entityId": "https://your-domain.com/api/auth/saml/metadata",
    "assertionConsumerService": {
      "url": "https://your-domain.com/api/auth/saml/acs"
    }
  },
  "idp": {
    "entityId": "https://your-idp.com/saml/metadata",
    "singleSignOnService": {
      "url": "https://your-idp.com/saml/sso"
    },
    "singleLogoutService": {
      "url": "https://your-idp.com/saml/slo"
    },
    "x509cert": "REPLACE_WITH_IDP_CERTIFICATE"
  }
}
```

---

## Docker로 전체 실행

```bash
docker compose up -d
```

서비스가 시작됩니다:
- **Backend API**: http://localhost:8001
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6380

> **주의**: Docker에서 USB 디바이스에 접근하려면 Linux 호스트 + `privileged` 모드가 필요합니다.
> Windows/macOS에서는 로컬 실행을 권장합니다.

---

## 연동 서비스

이 프로젝트는 [sqe_tc_bot (TC Generator)](https://github.com/cannewseebe-1919/sqe_tc_bot)와 함께 사용합니다.
TC Generator에서 AI로 생성한 테스트 코드를 이 서버가 실제 Android 단말에서 실행합니다.

**중요**: 두 서비스의 `JWT_SECRET` 값은 반드시 동일하게 설정해야 합니다.
