package com.testplatform.runner;

import android.os.Build;
import android.util.Base64;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

/**
 * Handles WebSocket communication with the Test Executor server.
 * Receives commands (get_ui_tree, screenshot, find_element, start_streaming, stop_streaming)
 * and sends back results as JSON.
 */
public class ServerCommunicator {

    private static final String TAG = "ServerCommunicator";
    private static final int NORMAL_CLOSURE = 1000;
    private static final long RECONNECT_DELAY_MS = 5000;

    private final OkHttpClient client;
    private WebSocket webSocket;
    private String serverUrl;
    private boolean shouldReconnect = false;
    private ConnectionListener connectionListener;

    public interface ConnectionListener {
        void onConnected();
        void onDisconnected(String reason);
        void onError(String error);
        void onLog(String message);
    }

    public ServerCommunicator() {
        client = new OkHttpClient.Builder()
                .readTimeout(0, TimeUnit.MILLISECONDS)   // No read timeout for WebSocket
                .pingInterval(30, TimeUnit.SECONDS)       // Keep alive
                .build();
    }

    public void setConnectionListener(ConnectionListener listener) {
        this.connectionListener = listener;
    }

    /**
     * Connect to the Test Executor server via WebSocket.
     *
     * @param url WebSocket URL (e.g., ws://host:port/ws/runner)
     */
    public void connect(String url) {
        this.serverUrl = url;
        this.shouldReconnect = true;

        Request request = new Request.Builder()
                .url(url)
                .addHeader("X-Device-Model", Build.MODEL)
                .addHeader("X-Device-SDK", String.valueOf(Build.VERSION.SDK_INT))
                .addHeader("X-Runner-Version", "1.0.0")
                .build();

        webSocket = client.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket ws, Response response) {
                Log.i(TAG, "WebSocket connected to " + serverUrl);
                if (connectionListener != null) {
                    connectionListener.onConnected();
                }
                // Send initial handshake
                sendDeviceInfo();
            }

            @Override
            public void onMessage(WebSocket ws, String text) {
                Log.d(TAG, "Message received: " + text);
                handleCommand(text);
            }

            @Override
            public void onClosing(WebSocket ws, int code, String reason) {
                Log.i(TAG, "WebSocket closing: " + code + " " + reason);
                ws.close(NORMAL_CLOSURE, null);
            }

            @Override
            public void onClosed(WebSocket ws, int code, String reason) {
                Log.i(TAG, "WebSocket closed: " + code + " " + reason);
                if (connectionListener != null) {
                    connectionListener.onDisconnected(reason);
                }
                scheduleReconnect();
            }

            @Override
            public void onFailure(WebSocket ws, Throwable t, Response response) {
                Log.e(TAG, "WebSocket failure: " + t.getMessage(), t);
                if (connectionListener != null) {
                    connectionListener.onError(t.getMessage());
                }
                scheduleReconnect();
            }
        });
    }

    /**
     * Disconnect from the server.
     */
    public void disconnect() {
        shouldReconnect = false;
        if (webSocket != null) {
            webSocket.close(NORMAL_CLOSURE, "Client disconnect");
            webSocket = null;
        }
        Log.i(TAG, "Disconnected from server");
    }

    public boolean isConnected() {
        return webSocket != null;
    }

    private void scheduleReconnect() {
        if (!shouldReconnect) {
            return;
        }
        Log.i(TAG, "Scheduling reconnect in " + RECONNECT_DELAY_MS + "ms");
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    Thread.sleep(RECONNECT_DELAY_MS);
                    if (shouldReconnect && serverUrl != null) {
                        Log.i(TAG, "Attempting reconnect...");
                        connect(serverUrl);
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        }).start();
    }

    private void sendDeviceInfo() {
        try {
            JSONObject info = new JSONObject();
            info.put("type", "device_info");
            info.put("model", Build.MODEL);
            info.put("manufacturer", Build.MANUFACTURER);
            info.put("sdk_version", Build.VERSION.SDK_INT);
            info.put("android_version", Build.VERSION.RELEASE);
            info.put("runner_version", "1.0.0");
            info.put("accessibility_active", TestRunnerAccessibilityService.isServiceActive());
            ScreenCaptureService scs = ScreenCaptureService.getInstance();
            info.put("screen_capture_active", scs != null && scs.isProjectionActive());
            sendMessage(info.toString());
        } catch (JSONException e) {
            Log.e(TAG, "Error sending device info", e);
        }
    }

    /**
     * Handle incoming command from the server.
     */
    private void handleCommand(String message) {
        try {
            JSONObject cmd = new JSONObject(message);
            String type = cmd.optString("type", "");
            String requestId = cmd.optString("request_id", "");

            logEvent("Command received: " + type);

            switch (type) {
                case "get_ui_tree":
                    handleGetUITree(requestId);
                    break;
                case "find_element":
                    handleFindElement(requestId, cmd);
                    break;
                case "screenshot":
                    handleScreenshot(requestId);
                    break;
                case "start_streaming":
                    handleStartStreaming(requestId, cmd);
                    break;
                case "stop_streaming":
                    handleStopStreaming(requestId);
                    break;
                case "ping":
                    handlePing(requestId);
                    break;
                default:
                    sendError(requestId, "Unknown command: " + type);
                    break;
            }
        } catch (JSONException e) {
            Log.e(TAG, "Error parsing command", e);
            sendError("", "Invalid JSON: " + e.getMessage());
        }
    }

    private void handleGetUITree(String requestId) {
        TestRunnerAccessibilityService service = TestRunnerAccessibilityService.getInstance();
        if (service == null) {
            sendError(requestId, "Accessibility service not active");
            return;
        }
        JSONObject tree = service.getUITree();
        try {
            JSONObject response = new JSONObject();
            response.put("type", "ui_tree_result");
            response.put("request_id", requestId);
            response.put("success", true);
            response.put("data", tree);
            sendMessage(response.toString());
            logEvent("UI tree sent (" + tree.toString().length() + " bytes)");
        } catch (JSONException e) {
            Log.e(TAG, "Error building UI tree response", e);
        }
    }

    private void handleFindElement(String requestId, JSONObject cmd) {
        TestRunnerAccessibilityService service = TestRunnerAccessibilityService.getInstance();
        if (service == null) {
            sendError(requestId, "Accessibility service not active");
            return;
        }
        String text = cmd.optString("text", null);
        String resourceId = cmd.optString("resource_id", null);
        String className = cmd.optString("class_name", null);

        JSONArray elements = service.findElements(text, resourceId, className);
        try {
            JSONObject response = new JSONObject();
            response.put("type", "find_element_result");
            response.put("request_id", requestId);
            response.put("success", true);
            response.put("count", elements.length());
            response.put("elements", elements);
            sendMessage(response.toString());
            logEvent("Found " + elements.length() + " elements");
        } catch (JSONException e) {
            Log.e(TAG, "Error building find element response", e);
        }
    }

    private void handleScreenshot(String requestId) {
        ScreenCaptureService scs = ScreenCaptureService.getInstance();
        if (scs == null || !scs.isProjectionActive()) {
            sendError(requestId, "Screen capture not active");
            return;
        }
        String base64 = scs.captureScreenshotBase64();
        if (base64 == null) {
            sendError(requestId, "Failed to capture screenshot");
            return;
        }
        try {
            JSONObject response = new JSONObject();
            response.put("type", "screenshot_result");
            response.put("request_id", requestId);
            response.put("success", true);
            response.put("format", "png");
            response.put("encoding", "base64");
            response.put("data", base64);
            sendMessage(response.toString());
            logEvent("Screenshot sent (" + base64.length() + " chars base64)");
        } catch (JSONException e) {
            Log.e(TAG, "Error building screenshot response", e);
        }
    }

    private void handleStartStreaming(String requestId, JSONObject cmd) {
        ScreenCaptureService scs = ScreenCaptureService.getInstance();
        if (scs == null || !scs.isProjectionActive()) {
            sendError(requestId, "Screen capture not active");
            return;
        }
        long intervalMs = cmd.optLong("interval_ms", 100); // Default ~10 FPS
        scs.startStreaming(new ScreenCaptureService.StreamCallback() {
            @Override
            public void onFrame(byte[] pngData) {
                try {
                    String base64 = Base64.encodeToString(pngData, Base64.NO_WRAP);
                    JSONObject frame = new JSONObject();
                    frame.put("type", "stream_frame");
                    frame.put("format", "png");
                    frame.put("encoding", "base64");
                    frame.put("data", base64);
                    sendMessage(frame.toString());
                } catch (JSONException e) {
                    Log.e(TAG, "Error sending stream frame", e);
                }
            }
        }, intervalMs);

        try {
            JSONObject response = new JSONObject();
            response.put("type", "streaming_started");
            response.put("request_id", requestId);
            response.put("success", true);
            response.put("interval_ms", intervalMs);
            sendMessage(response.toString());
            logEvent("Streaming started (interval: " + intervalMs + "ms)");
        } catch (JSONException e) {
            Log.e(TAG, "Error sending streaming response", e);
        }
    }

    private void handleStopStreaming(String requestId) {
        ScreenCaptureService scs = ScreenCaptureService.getInstance();
        if (scs != null) {
            scs.stopStreaming();
        }
        try {
            JSONObject response = new JSONObject();
            response.put("type", "streaming_stopped");
            response.put("request_id", requestId);
            response.put("success", true);
            sendMessage(response.toString());
            logEvent("Streaming stopped");
        } catch (JSONException e) {
            Log.e(TAG, "Error sending stop streaming response", e);
        }
    }

    private void handlePing(String requestId) {
        try {
            JSONObject response = new JSONObject();
            response.put("type", "pong");
            response.put("request_id", requestId);
            response.put("accessibility_active", TestRunnerAccessibilityService.isServiceActive());
            ScreenCaptureService scs = ScreenCaptureService.getInstance();
            response.put("screen_capture_active", scs != null && scs.isProjectionActive());
            sendMessage(response.toString());
        } catch (JSONException e) {
            Log.e(TAG, "Error sending pong", e);
        }
    }

    private void sendError(String requestId, String errorMessage) {
        try {
            JSONObject response = new JSONObject();
            response.put("type", "error");
            response.put("request_id", requestId);
            response.put("success", false);
            response.put("error", errorMessage);
            sendMessage(response.toString());
            logEvent("Error: " + errorMessage);
        } catch (JSONException e) {
            Log.e(TAG, "Error sending error response", e);
        }
    }

    private void sendMessage(String message) {
        if (webSocket != null) {
            webSocket.send(message);
        } else {
            Log.w(TAG, "Cannot send message - WebSocket not connected");
        }
    }

    private void logEvent(String message) {
        Log.i(TAG, message);
        if (connectionListener != null) {
            connectionListener.onLog(message);
        }
    }
}
