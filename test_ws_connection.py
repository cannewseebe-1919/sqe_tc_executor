"""
Runner App WebSocket 연결 테스트 스크립트.

실제 APK 없이 Runner App이 하는 동작을 Python으로 시뮬레이션합니다.
실제 단말에 APK를 설치한 경우에는 이 스크립트 대신 APK를 사용합니다.

사용법:
  python test_ws_connection.py [DEVICE_ID] [SERVER_URL]

  DEVICE_ID  : 시뮬레이션할 단말 ID (기본값: emulator-5554)
  SERVER_URL : 백엔드 WS URL (기본값: ws://localhost:8001/ws/runner)

테스트 순서:
  1. WebSocket 연결
  2. device_info 전송
  3. ping 수신 시 pong 응답
  4. get_ui_tree / find_element / screenshot 명령 수신 시 더미 응답
  5. Ctrl+C 로 종료
"""

import asyncio
import json
import sys
import base64
import io

# Windows cp949 환경에서도 출력되도록 UTF-8 강제 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import websockets
except ImportError:
    print("[오류] websockets 패키지가 없습니다.")
    print("  설치: pip install websockets")
    sys.exit(1)

DEVICE_ID = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
SERVER_URL = sys.argv[2] if len(sys.argv) > 2 else "ws://localhost:8001/ws/runner"

DUMMY_UI_TREE = {
    "package": "com.example.app",
    "activity": "MainActivity",
    "root": {
        "class": "android.widget.FrameLayout",
        "bounds": {"left": 0, "top": 0, "right": 1080, "bottom": 2340},
        "children": [
            {
                "class": "android.widget.TextView",
                "text": "Hello World",
                "resource-id": "com.example.app:id/hello_text",
                "bounds": {"left": 100, "top": 500, "right": 980, "bottom": 600},
                "clickable": True,
            }
        ],
    },
}

DUMMY_PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32).decode()


async def handle_command(ws, msg: dict):
    cmd_type = msg.get("type", "")
    request_id = msg.get("request_id", "")
    print(f"  [명령 수신] type={cmd_type}, request_id={request_id[:8]}...")

    if cmd_type == "get_ui_tree":
        response = {
            "type": "ui_tree_result",
            "request_id": request_id,
            "success": True,
            "data": DUMMY_UI_TREE,
        }

    elif cmd_type == "find_element":
        text = msg.get("text", "")
        resource_id = msg.get("resource_id", "")
        response = {
            "type": "find_element_result",
            "request_id": request_id,
            "success": True,
            "count": 1,
            "elements": [
                {
                    "text": text or "Hello World",
                    "resource-id": resource_id or "com.example.app:id/hello_text",
                    "class": "android.widget.TextView",
                    "bounds": {"left": 100, "top": 500, "right": 980, "bottom": 600},
                    "clickable": True,
                }
            ],
        }

    elif cmd_type == "screenshot":
        response = {
            "type": "screenshot_result",
            "request_id": request_id,
            "success": True,
            "format": "png",
            "encoding": "base64",
            "data": DUMMY_PNG,
        }

    elif cmd_type == "ping":
        response = {
            "type": "pong",
            "request_id": request_id,
            "accessibility_active": True,
            "screen_capture_active": True,
        }

    elif cmd_type in ("start_streaming", "stop_streaming"):
        response = {
            "type": "streaming_started" if cmd_type == "start_streaming" else "streaming_stopped",
            "request_id": request_id,
            "success": True,
        }

    else:
        response = {
            "type": "error",
            "request_id": request_id,
            "success": False,
            "error": f"Unknown command: {cmd_type}",
        }

    await ws.send(json.dumps(response))
    print(f"  [응답 전송] type={response['type']}")


async def main():
    print(f"[*] Runner App 시뮬레이터 시작")
    print(f"    DEVICE_ID : {DEVICE_ID}")
    print(f"    SERVER_URL: {SERVER_URL}")
    print()

    headers = {
        "X-Device-Model": "Simulated Galaxy",
        "X-Device-SDK": "34",
        "X-Runner-Version": "1.0.0",
    }

    try:
        async with websockets.connect(SERVER_URL, additional_headers=headers) as ws:
            print("[✓] WebSocket 연결 성공!")

            # 1. device_info 전송
            device_info = {
                "type": "device_info",
                "device_id": DEVICE_ID,
                "model": "Simulated Galaxy S24",
                "manufacturer": "Samsung",
                "sdk_version": 34,
                "android_version": "14",
                "runner_version": "1.0.0",
                "accessibility_active": True,
                "screen_capture_active": True,
            }
            await ws.send(json.dumps(device_info))
            print(f"[✓] device_info 전송 완료 (device_id={DEVICE_ID})")
            print()
            print("[*] 명령 대기 중... (Ctrl+C로 종료)")
            print()

            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    await handle_command(ws, msg)
                except json.JSONDecodeError:
                    print(f"  [경고] JSON 파싱 실패: {raw[:100]}")

    except ConnectionRefusedError:
        print(f"[✗] 연결 실패: {SERVER_URL} 에 서버가 없습니다.")
        print("    백엔드 서버가 실행 중인지 확인하세요:")
        print("    cd backend && venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8001")
    except Exception as e:
        print(f"[✗] 오류: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] 시뮬레이터 종료")
