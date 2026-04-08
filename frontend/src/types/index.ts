// Device statuses
export type DeviceStatus = 'CONNECTED' | 'TESTING' | 'QUEUED' | 'OFFLINE' | 'ERROR';

// Execution statuses
export type ExecutionStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'ABORTED';

// Step statuses
export type StepStatus = 'PASSED' | 'FAILED' | 'SKIPPED';

// Error types
export type ErrorType =
  | 'ASSERTION_FAILED'
  | 'ELEMENT_NOT_FOUND'
  | 'STEP_TIMEOUT'
  | 'APP_CRASH'
  | 'ANR'
  | 'KERNEL_PANIC'
  | 'SYSTEM_UI_CRASH'
  | 'ADB_ERROR';

export interface Device {
  id: string;
  name: string;
  model: string;
  android_version: string;
  resolution: string;
  status: DeviceStatus;
  connected_at: string;
  last_seen_at: string;
  queue_length: number;
}

export interface ExecutionStep {
  execution_id: string;
  step_name: string;
  step_order: number;
  status: StepStatus;
  duration_sec: number;
  screenshot_url: string | null;
  log: string;
  error_type: ErrorType | null;
}

export interface Execution {
  id: string;
  test_case_id: string;
  device_id: string;
  device_name?: string;
  requested_by: string;
  status: ExecutionStatus;
  queue_position: number;
  started_at: string | null;
  finished_at: string | null;
  total_duration_sec: number | null;
  current_step?: string;
  progress?: string;
  summary?: {
    total_steps: number;
    passed: number;
    failed: number;
    aborted: boolean;
    abort_reason: string | null;
  };
  steps?: ExecutionStep[];
  crash_logs?: string[];
  device_info?: {
    model: string;
    android_version: string;
    resolution: string;
  };
}

export interface QueueItem {
  execution_id: string;
  test_case_id: string;
  requested_by: string;
  queued_at: string;
  position: number;
}

export interface DeviceQueue {
  device_id: string;
  device_name: string;
  current_execution: Execution | null;
  queue: QueueItem[];
}

export interface User {
  email: string;
  name: string;
  department: string;
}
