package com.testplatform.runner;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.media.projection.MediaProjectionManager;
import android.os.Bundle;
import android.provider.Settings;
import android.text.method.ScrollingMovementMethod;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

/**
 * Main activity for the Test Runner app.
 * Provides UI for:
 * - Enabling the AccessibilityService
 * - Setting up MediaProjection for screen capture
 * - Connecting to the Test Executor server via WebSocket
 */
public class MainActivity extends AppCompatActivity {

    private static final String TAG = "MainActivity";
    private static final int REQUEST_MEDIA_PROJECTION = 1001;
    private static final String PREFS_NAME = "runner_prefs";
    private static final String PREF_SERVER_URL = "server_url";

    private TextView tvAccessibilityStatus;
    private Button btnAccessibility;
    private EditText etServerUrl;
    private TextView tvConnectionStatus;
    private Button btnConnect;
    private TextView tvLog;

    private ServerCommunicator serverCommunicator;
    private boolean isConnected = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvAccessibilityStatus = findViewById(R.id.tvAccessibilityStatus);
        btnAccessibility = findViewById(R.id.btnAccessibility);
        etServerUrl = findViewById(R.id.etServerUrl);
        tvConnectionStatus = findViewById(R.id.tvConnectionStatus);
        btnConnect = findViewById(R.id.btnConnect);
        tvLog = findViewById(R.id.tvLog);
        tvLog.setMovementMethod(new ScrollingMovementMethod());

        // Load saved server URL
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String savedUrl = prefs.getString(PREF_SERVER_URL, "");
        if (!savedUrl.isEmpty()) {
            etServerUrl.setText(savedUrl);
        }

        serverCommunicator = new ServerCommunicator();
        serverCommunicator.setConnectionListener(new ServerCommunicator.ConnectionListener() {
            @Override
            public void onConnected() {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        isConnected = true;
                        tvConnectionStatus.setText(R.string.status_connected);
                        tvConnectionStatus.setTextColor(0xFF4CAF50); // Green
                        btnConnect.setText(R.string.btn_disconnect_server);
                        appendLog("Connected to server");
                    }
                });
            }

            @Override
            public void onDisconnected(final String reason) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        isConnected = false;
                        tvConnectionStatus.setText(R.string.status_disconnected);
                        tvConnectionStatus.setTextColor(0xFFF44336); // Red
                        btnConnect.setText(R.string.btn_connect_server);
                        appendLog("Disconnected: " + reason);
                    }
                });
            }

            @Override
            public void onError(final String error) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        appendLog("Error: " + error);
                    }
                });
            }

            @Override
            public void onLog(final String message) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        appendLog(message);
                    }
                });
            }
        });

        // Accessibility settings button
        btnAccessibility.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
                startActivity(intent);
            }
        });

        // Connect button
        btnConnect.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (isConnected) {
                    serverCommunicator.disconnect();
                } else {
                    String url = etServerUrl.getText().toString().trim();
                    if (url.isEmpty()) {
                        appendLog("Please enter server URL");
                        return;
                    }
                    // Save URL
                    getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                            .edit().putString(PREF_SERVER_URL, url).apply();

                    tvConnectionStatus.setText(R.string.status_connecting);
                    tvConnectionStatus.setTextColor(0xFFFF9800); // Orange
                    appendLog("Connecting to " + url + "...");

                    // Request screen capture permission before connecting
                    requestScreenCapture();

                    serverCommunicator.connect(url);
                }
            }
        });

        Log.i(TAG, "MainActivity created");
        appendLog("Test Runner started");
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateAccessibilityStatus();
    }

    @Override
    protected void onDestroy() {
        if (serverCommunicator != null) {
            serverCommunicator.disconnect();
        }
        super.onDestroy();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_MEDIA_PROJECTION) {
            if (resultCode == Activity.RESULT_OK && data != null) {
                Log.i(TAG, "MediaProjection permission granted");
                appendLog("Screen capture permission granted");
                startScreenCaptureService(resultCode, data);
            } else {
                Log.w(TAG, "MediaProjection permission denied");
                appendLog("Screen capture permission denied");
            }
        }
    }

    private void requestScreenCapture() {
        ScreenCaptureService scs = ScreenCaptureService.getInstance();
        if (scs != null && scs.isProjectionActive()) {
            // Already active
            return;
        }
        MediaProjectionManager projectionManager =
                (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        startActivityForResult(projectionManager.createScreenCaptureIntent(), REQUEST_MEDIA_PROJECTION);
    }

    private void startScreenCaptureService(int resultCode, Intent data) {
        Intent serviceIntent = new Intent(this, ScreenCaptureService.class);
        serviceIntent.putExtra("resultCode", resultCode);
        serviceIntent.putExtra("data", data);
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }

    private void updateAccessibilityStatus() {
        boolean active = TestRunnerAccessibilityService.isServiceActive();
        if (active) {
            tvAccessibilityStatus.setText(R.string.accessibility_enabled);
            tvAccessibilityStatus.setTextColor(0xFF4CAF50); // Green
        } else {
            tvAccessibilityStatus.setText(R.string.accessibility_disabled);
            tvAccessibilityStatus.setTextColor(0xFFF44336); // Red
        }
    }

    private void appendLog(String message) {
        String timestamp = new java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
                .format(new java.util.Date());
        String line = "[" + timestamp + "] " + message + "\n";
        tvLog.append(line);
        Log.d(TAG, message);
    }
}
