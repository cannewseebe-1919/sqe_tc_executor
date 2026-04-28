import { useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Play, ChevronDown } from 'lucide-react';
import { executeTest } from '../../services/api';
import type { Device } from '../../types';

// ─── TC 프리셋 ──────────────────────────────────────────────────────────────
const PRESETS: { label: string; code: string }[] = [
  {
    label: '비행기 모드 ON/OFF',
    code: `import time

from device import device
from decorators import step, ElementNotFoundError


class AirplaneModeTC:
    """비행기 모드 켜기/끄기 테스트"""

    @step("초기 화면 캡처")
    def step_01_initial_screenshot(self):
        device.screenshot("01_before")

    @step("비행기 모드 켜기")
    def step_02_enable_airplane(self):
        device._adb_shell("cmd connectivity airplane-mode enable")
        device.wait(2)
        state = device._adb_shell("settings get global airplane_mode_on")
        assert state.strip() == "1", f"비행기 모드 ON 실패 (현재값: {state})"

    @step("비행기 모드 ON 화면 캡처")
    def step_03_screenshot_on(self):
        device.screenshot("02_airplane_on")

    @step("비행기 모드 끄기")
    def step_04_disable_airplane(self):
        device._adb_shell("cmd connectivity airplane-mode disable")
        device.wait(3)
        state = device._adb_shell("settings get global airplane_mode_on")
        assert state.strip() == "0", f"비행기 모드 OFF 실패 (현재값: {state})"

    @step("비행기 모드 OFF 화면 캡처")
    def step_05_screenshot_off(self):
        device.screenshot("03_airplane_off")


tc = AirplaneModeTC()
tc.step_01_initial_screenshot()
tc.step_02_enable_airplane()
tc.step_03_screenshot_on()
tc.step_04_disable_airplane()
tc.step_05_screenshot_off()
`,
  },
  {
    label: '기기 정보 수집',
    code: `from device import device
from decorators import step


class DeviceInfoTC:
    """기기 기본 정보 수집"""

    @step("모델명 확인")
    def step_01_model(self):
        model = device._adb_shell("getprop ro.product.model")
        assert model, "모델명을 가져올 수 없음"

    @step("Android 버전 확인")
    def step_02_android_version(self):
        ver = device._adb_shell("getprop ro.build.version.release")
        assert ver, "Android 버전을 가져올 수 없음"

    @step("화면 해상도 확인")
    def step_03_resolution(self):
        size = device._adb_shell("wm size")
        assert "Physical size" in size or "Override size" in size or "x" in size, \
            f"해상도 정보 없음: {size}"

    @step("배터리 상태 확인")
    def step_04_battery(self):
        battery = device._adb_shell("dumpsys battery | grep level")
        assert battery, "배터리 정보를 가져올 수 없음"

    @step("화면 캡처")
    def step_05_screenshot(self):
        device.screenshot("device_info")


tc = DeviceInfoTC()
tc.step_01_model()
tc.step_02_android_version()
tc.step_03_resolution()
tc.step_04_battery()
tc.step_05_screenshot()
`,
  },
  {
    label: '볼륨 UP/DOWN',
    code: `import time

from device import device
from decorators import step


class VolumeControlTC:
    """볼륨 조절 키 동작 테스트"""

    @step("초기 화면 캡처")
    def step_01_screenshot_before(self):
        device.screenshot("01_before")

    @step("볼륨 올리기 (3회)")
    def step_02_volume_up(self):
        for _ in range(3):
            device.press_key("volume_up")
            time.sleep(0.5)

    @step("볼륨 UP 상태 화면 캡처")
    def step_03_screenshot_up(self):
        device.screenshot("02_volume_up")

    @step("볼륨 내리기 (3회)")
    def step_04_volume_down(self):
        for _ in range(3):
            device.press_key("volume_down")
            time.sleep(0.5)

    @step("볼륨 DOWN 상태 화면 캡처")
    def step_05_screenshot_down(self):
        device.screenshot("03_volume_down")


tc = VolumeControlTC()
tc.step_01_screenshot_before()
tc.step_02_volume_up()
tc.step_03_screenshot_up()
tc.step_04_volume_down()
tc.step_05_screenshot_down()
`,
  },
];

interface Props {
  device: Device;
  onClose: () => void;
  onSubmitted: (executionId: string) => void;
}

export default function ExecuteModal({ device, onClose, onSubmitted }: Props) {
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [code, setCode] = useState(PRESETS[0].code);
  const [requestedBy, setRequestedBy] = useState('developer');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [presetOpen, setPresetOpen] = useState(false);

  const handlePresetSelect = (idx: number) => {
    setSelectedPreset(idx);
    setCode(PRESETS[idx].code);
    setPresetOpen(false);
  };

  const handleSubmit = async () => {
    if (!code.trim()) { setError('TC 코드를 입력해주세요.'); return; }
    if (!requestedBy.trim()) { setError('요청자를 입력해주세요.'); return; }
    setSubmitting(true);
    setError(null);
    try {
      const result = await executeTest({
        device_id: device.id,
        test_code: code,
        requested_by: requestedBy.trim(),
      });
      onSubmitted(result.execution_id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '실행 요청 실패';
      setError(msg);
      setSubmitting(false);
    }
  };

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(4px)',
          zIndex: 200,
        }}
      />

      {/* Modal */}
      <div style={{
        position: 'fixed',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 201,
        width: 740,
        maxWidth: 'calc(100vw - 48px)',
        maxHeight: 'calc(100vh - 80px)',
        background: 'var(--card)',
        border: '1px solid var(--border-hover)',
        borderRadius: 16,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 32px 80px rgba(0,0,0,0.6)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '18px 24px',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--heading)' }}>
              TC 실행
            </div>
            <div style={{ fontSize: 12, color: 'var(--text)', opacity: 0.6, marginTop: 2 }}>
              {device.name} · {device.model}
            </div>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text)', padding: 4, borderRadius: 6,
          }}>
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Preset selector */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 8, opacity: 0.7, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              TC 프리셋
            </div>
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setPresetOpen((v) => !v)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px', background: 'var(--elevated)',
                  border: '1px solid var(--border)', borderRadius: 8,
                  color: 'var(--heading)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
                }}
              >
                <span>{PRESETS[selectedPreset].label}</span>
                <ChevronDown size={14} style={{ color: 'var(--text)', flexShrink: 0 }} />
              </button>
              {presetOpen && (
                <div style={{
                  position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
                  background: 'var(--elevated)', border: '1px solid var(--border)',
                  borderRadius: 8, zIndex: 10, overflow: 'hidden',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                }}>
                  {PRESETS.map((p, i) => (
                    <button
                      key={i}
                      onClick={() => handlePresetSelect(i)}
                      style={{
                        display: 'block', width: '100%', padding: '10px 14px',
                        textAlign: 'left', background: i === selectedPreset ? 'var(--accent-dim)' : 'none',
                        border: 'none', color: i === selectedPreset ? '#93c5fd' : 'var(--text-bright)',
                        fontSize: 13, cursor: 'pointer', transition: 'background 0.1s',
                      }}
                      onMouseEnter={(e) => { if (i !== selectedPreset) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'; }}
                      onMouseLeave={(e) => { if (i !== selectedPreset) (e.currentTarget as HTMLElement).style.background = 'none'; }}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Code editor */}
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 8, opacity: 0.7, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              TC 코드
            </div>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              spellCheck={false}
              style={{
                width: '100%', height: 300,
                background: '#020810',
                border: '1px solid var(--border)',
                borderRadius: 8,
                color: '#e2e8f0',
                fontSize: 12,
                fontFamily: 'ui-monospace, Consolas, monospace',
                lineHeight: 1.6,
                padding: 14,
                resize: 'vertical',
                outline: 'none',
                boxSizing: 'border-box',
                transition: 'border-color 0.15s',
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
              onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
            />
          </div>

          {/* Requested by */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 8, opacity: 0.7, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              요청자
            </div>
            <input
              value={requestedBy}
              onChange={(e) => setRequestedBy(e.target.value)}
              placeholder="이름 또는 ID"
              style={{
                width: '100%', padding: '10px 14px',
                background: 'var(--elevated)', border: '1px solid var(--border)',
                borderRadius: 8, color: 'var(--heading)', fontSize: 13, outline: 'none',
                boxSizing: 'border-box', transition: 'border-color 0.15s',
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
              onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
            />
          </div>

          {/* Error */}
          {error && (
            <div style={{
              padding: '10px 14px', borderRadius: 8, fontSize: 13,
              background: 'var(--error-dim)', color: '#fca5a5',
              border: '1px solid rgba(239,68,68,0.25)',
            }}>
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10,
          padding: '16px 24px', borderTop: '1px solid var(--border)', flexShrink: 0,
        }}>
          <button className="btn btn-ghost" onClick={onClose} disabled={submitting}>
            취소
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={submitting}
            style={{ minWidth: 100 }}
          >
            {submitting ? (
              <>
                <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span>
                제출 중...
              </>
            ) : (
              <>
                <Play size={13} />
                TC 실행
              </>
            )}
          </button>
        </div>
      </div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </>,
    document.body
  );
}
