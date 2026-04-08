import axios from 'axios';
import type { Device, Execution, DeviceQueue } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token from session
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

// --- Device APIs ---
export async function getDevices(): Promise<Device[]> {
  const { data } = await api.get<{ devices: Device[] }>('/devices');
  return data.devices;
}

export async function updateDeviceName(deviceId: string, name: string): Promise<Device> {
  const { data } = await api.patch<Device>(`/devices/${deviceId}`, { name });
  return data;
}

// --- Execution APIs ---
export async function getExecutions(params?: {
  device_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ executions: Execution[]; total: number }> {
  const { data } = await api.get('/executions', { params });
  return data;
}

export async function getExecution(executionId: string): Promise<Execution> {
  const { data } = await api.get<Execution>(`/execute/${executionId}/status`);
  return data;
}

export async function executeTest(payload: {
  test_code: string;
  device_id: string;
  requested_by: string;
  callback_url?: string;
}): Promise<{ execution_id: string; status: string; queue_position: number }> {
  const { data } = await api.post('/execute', payload);
  return data;
}

// --- Queue APIs ---
export async function getQueues(): Promise<DeviceQueue[]> {
  const { data } = await api.get<{ queues: DeviceQueue[] }>('/queues');
  return data.queues;
}

// --- Auth APIs ---
export async function getSamlLoginUrl(): Promise<string> {
  const { data } = await api.get<{ url: string }>('/auth/saml/login');
  return data.url;
}

export async function getCurrentUser() {
  const { data } = await api.get('/auth/me');
  return data;
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout');
  localStorage.removeItem('access_token');
}

// --- Streaming ---
export function createStreamWebSocket(deviceId: string): WebSocket {
  const wsBase = import.meta.env.VITE_WS_BASE_URL ||
    `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
  return new WebSocket(`${wsBase}/api/devices/${deviceId}/stream`);
}

export default api;
