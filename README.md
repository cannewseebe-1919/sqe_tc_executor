# SQE Test Executor

Android 단말 테스트 자동 실행 서버입니다.
USB로 연결된 Android 디바이스를 관리하고, ADB + Runner App을 통해 테스트 케이스를 실행하며, 실시간 화면 스트리밍과 FIFO 스케줄링을 제공합니다.

## 아키텍처

```
[Browser] ←→ [React Frontend :3001] ←→ [FastAPI Backend :8001] ←→ [ADB] ←→ [Android Devices]
                                              ↕                        ↕
                                     [PostgreSQL] [Redis]       [Runner App]
                                              ↕                  (on device)
                                     [TC Generator :8000]
```

## 사전 요구사항

- **Docker** & **Docker Compose** (권장)
- 또는 로컬 실행 시:
  - Python 3.12+
  - Node.js 18+ & npm
  - PostgreSQL 16
  - Redis 7
- **ADB** (Android Debug Bridge) — Android SDK Platform-Tools
- **scrcpy** — 실시간 화면 스트리밍용 (선택)
- USB로 연결된 Android 디바이스 (USB 디버깅 활성화)

## 빠른 시작 (Docker)

### 1. 저장소 클론

```bash
git clone https://github.com/cannewseebe-1919/sqe_tc_executor.git
cd sqe_tc_executor
```

### 2. 환경변수 설정

`backend/.env` 파일을 생성합니다:

```env
# JWT 시크릿 (TC Generator와 동일한 값 사용, 반드시 변경)
JWT_SECRET=your-strong-random-secret

# ADB 경로 (Docker 컨테이너 내부에서는 기본값 사용)
ADB_PATH=adb

# scrcpy 경로 (화면 스트리밍용)
SCRCPY_PATH=scrcpy

# CORS 허용 도메인
CORS_ORIGINS=["http://localhost:3001","http://localhost:3000"]
```

### 3. SAML IdP 설정

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

### 4. Android 디바이스 준비

```bash
# USB 디버깅이 활성화된 디바이스를 USB로 연결
adb devices  # 디바이스가 목록에 표시되는지 확인
```

### 5. Runner App 빌드 및 설치 (선택)

Runner App은 디바이스에서 UI 트리 탐색, 스크린샷, 화면 스트리밍을 담당합니다.

```bash
cd runner-app
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

> Runner App 없이도 기본 ADB 명령 기반 테스트는 실행 가능합니다.

### 6. 실행

```bash
docker compose up -d
```

서비스가 시작됩니다:
- **Backend API**: http://localhost:8001
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6380

> **참고**: Docker에서 USB 디바이스에 접근하려면 Linux 호스트 + `privileged` 모드가 필요합니다.
> Windows/macOS에서는 로컬 실행을 권장합니다.

### 7. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

프론트엔드: http://localhost:3001

## 로컬 실행 (Docker 없이) — 권장

USB 디바이스 접근이 필요하므로 로컬 실행을 권장합니다.

### Backend

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성 (위 환경변수 설정 참고)

# PostgreSQL, Redis 실행 (Docker로 DB만 실행 가능)
docker compose up -d db redis

# DB 마이그레이션
alembic upgrade head

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 환경변수 전체 목록

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 접속 URL | `postgresql+asyncpg://postgres:postgres@localhost:5432/test_executor` |
| `REDIS_URL` | Redis 접속 URL | `redis://localhost:6379/0` |
| `ADB_PATH` | ADB 실행 파일 경로 | `adb` |
| `ADB_POLL_INTERVAL` | 디바이스 탐지 폴링 간격(초) | `5` |
| `RUNNER_APP_PORT` | Runner App 통신 포트 | `8080` |
| `RUNNER_APP_APK_PATH` | Runner App APK 경로 | `runner-app/app/build/outputs/apk/debug/app-debug.apk` |
| `SCRCPY_PATH` | scrcpy 실행 파일 경로 | `scrcpy` |
| `JWT_SECRET` | JWT 서명 시크릿 (TC Generator와 동일) | `change-me-in-production` |
| `JWT_ALGORITHM` | JWT 알고리즘 | `HS256` |
| `JWT_EXPIRE_MINUTES` | JWT 만료 시간(분) | `60` |
| `DEFAULT_STEP_TIMEOUT` | TC 스텝 실행 타임아웃(초) | `30` |
| `SCREENSHOT_DIR` | 스크린샷 저장 디렉토리 | `screenshots` |
| `LOG_DIR` | 로그 저장 디렉토리 | `logs` |
| `LOGCAT_POLL_INTERVAL` | 크래시 감지 logcat 폴링(초) | `0.5` |
| `SAML_SETTINGS_PATH` | SAML 설정 파일 경로 | `app/core/saml/settings.json` |
| `CORS_ORIGINS` | 허용 CORS 도메인 | `["http://localhost:3000","http://localhost:3001"]` |
| `DEBUG` | 디버그 모드 | `false` |

## 주요 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | 헬스체크 |
| GET | `/api/auth/saml/login` | SAML SSO 로그인 |
| POST | `/api/auth/saml/acs` | SAML ACS 콜백 |
| GET | `/api/devices` | 연결된 디바이스 목록 |
| GET | `/api/devices/{serial}` | 디바이스 상세 정보 |
| POST | `/api/execution` | TC 실행 요청 (FIFO 큐 등록) |
| GET | `/api/execution/{id}` | 실행 상태/결과 조회 |
| GET | `/api/execution/{id}/steps` | 스텝별 실행 결과 |
| WS | `/api/streaming/{serial}` | 디바이스 실시간 화면 스트리밍 |
| WS | `/api/streaming/execution/{id}` | 실행 중 화면 스트리밍 |

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
│   │   ├── sdk/           # test_executor_sdk (TestCase, @step, Device, assertions)
│   │   └── services/      # ADB, 디바이스 모니터, 스케줄러, 크래시 감지, 스트리밍
│   ├── alembic/           # DB 마이그레이션
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

## 디바이스 설정 가이드

### USB 디버깅 활성화

1. Android 기기에서 **설정 → 휴대전화 정보 → 빌드번호** 7회 탭 → 개발자 옵션 활성화
2. **설정 → 개발자 옵션 → USB 디버깅** 활성화
3. USB 연결 후 기기에서 "USB 디버깅 허용" 대화상자 승인

### Runner App 권한 설정

Runner App 설치 후 다음 권한을 수동으로 활성화해야 합니다:

1. **접근성 서비스**: 설정 → 접근성 → TestRunner → 활성화 (UI 트리 탐색용)
2. **화면 오버레이**: 설정 → 앱 → TestRunner → 다른 앱 위에 표시 허용 (스크린샷/스트리밍용)

## 연동 서비스

이 프로젝트는 [TC Generator](https://github.com/cannewseebe-1919/sqe_tc_bot)와 함께 사용합니다.
TC Generator에서 AI로 생성한 테스트 코드를 이 서버에서 실제 Android 단말로 실행합니다.

**중요**: 두 서비스의 `JWT_SECRET` 값은 반드시 동일하게 설정해야 합니다.
