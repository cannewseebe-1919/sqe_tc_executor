package com.testplatform.runner;

import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.util.Base64;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.WindowManager;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;

/**
 * Service for screen capture using MediaProjection API.
 * Supports single screenshot capture and continuous frame streaming.
 */
public class ScreenCaptureService extends Service {

    private static final String TAG = "ScreenCaptureService";
    private static final String CHANNEL_ID = "screen_capture_channel";
    private static final int NOTIFICATION_ID = 1001;

    private static ScreenCaptureService instance;

    private MediaProjectionManager projectionManager;
    private MediaProjection mediaProjection;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;
    private HandlerThread handlerThread;
    private Handler backgroundHandler;

    private int screenWidth;
    private int screenHeight;
    private int screenDensity;

    private boolean isStreaming = false;
    private StreamCallback streamCallback;

    public interface StreamCallback {
        void onFrame(byte[] pngData);
    }

    public static ScreenCaptureService getInstance() {
        return instance;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        projectionManager = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);

        // Get screen metrics
        WindowManager wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
        DisplayMetrics metrics = new DisplayMetrics();
        wm.getDefaultDisplay().getMetrics(metrics);
        screenWidth = metrics.widthPixels;
        screenHeight = metrics.heightPixels;
        screenDensity = metrics.densityDpi;

        // Background thread for image processing
        handlerThread = new HandlerThread("ScreenCapture");
        handlerThread.start();
        backgroundHandler = new Handler(handlerThread.getLooper());

        Log.i(TAG, "ScreenCaptureService created. Screen: " + screenWidth + "x" + screenHeight);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        createNotificationChannel();
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        Notification notification = builder
                .setContentTitle("Test Runner")
                .setContentText("Screen capture active")
                .setSmallIcon(android.R.drawable.ic_menu_camera)
                .build();
        startForeground(NOTIFICATION_ID, notification);

        if (intent != null) {
            int resultCode = intent.getIntExtra("resultCode", Activity.RESULT_CANCELED);
            Intent data = intent.getParcelableExtra("data");
            if (resultCode == Activity.RESULT_OK && data != null) {
                setupMediaProjection(resultCode, data);
            }
        }

        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        stopProjection();
        if (handlerThread != null) {
            handlerThread.quitSafely();
        }
        instance = null;
        Log.i(TAG, "ScreenCaptureService destroyed");
        super.onDestroy();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "Screen Capture", NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("Notification for screen capture service");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    private void setupMediaProjection(int resultCode, Intent data) {
        mediaProjection = projectionManager.getMediaProjection(resultCode, data);
        if (mediaProjection == null) {
            Log.e(TAG, "Failed to create MediaProjection");
            return;
        }

        mediaProjection.registerCallback(new MediaProjection.Callback() {
            @Override
            public void onStop() {
                Log.i(TAG, "MediaProjection stopped");
                cleanupVirtualDisplay();
            }
        }, backgroundHandler);

        createVirtualDisplay();
        Log.i(TAG, "MediaProjection setup complete");
    }

    private void createVirtualDisplay() {
        imageReader = ImageReader.newInstance(screenWidth, screenHeight, PixelFormat.RGBA_8888, 2);
        virtualDisplay = mediaProjection.createVirtualDisplay(
                "TestRunnerCapture",
                screenWidth, screenHeight, screenDensity,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.getSurface(),
                null, backgroundHandler);
        Log.i(TAG, "VirtualDisplay created");
    }

    private void cleanupVirtualDisplay() {
        if (virtualDisplay != null) {
            virtualDisplay.release();
            virtualDisplay = null;
        }
        if (imageReader != null) {
            imageReader.close();
            imageReader = null;
        }
    }

    private void stopProjection() {
        isStreaming = false;
        cleanupVirtualDisplay();
        if (mediaProjection != null) {
            mediaProjection.stop();
            mediaProjection = null;
        }
    }

    /**
     * Capture a single screenshot and return as PNG byte array.
     *
     * @return PNG-encoded byte array, or null on failure
     */
    public byte[] captureScreenshot() {
        if (imageReader == null) {
            Log.e(TAG, "ImageReader not initialized - MediaProjection not started");
            return null;
        }

        Image image = null;
        try {
            // Give time for a frame to be available
            Thread.sleep(100);
            image = imageReader.acquireLatestImage();
            if (image == null) {
                Log.w(TAG, "No image available from ImageReader");
                return null;
            }
            return imageToBytes(image);
        } catch (Exception e) {
            Log.e(TAG, "Error capturing screenshot", e);
            return null;
        } finally {
            if (image != null) {
                image.close();
            }
        }
    }

    /**
     * Capture a screenshot and return as Base64-encoded string.
     *
     * @return Base64-encoded PNG string, or null on failure
     */
    public String captureScreenshotBase64() {
        byte[] png = captureScreenshot();
        if (png == null) {
            return null;
        }
        return Base64.encodeToString(png, Base64.NO_WRAP);
    }

    /**
     * Start continuous frame streaming.
     *
     * @param callback receives each frame as PNG byte array
     * @param intervalMs milliseconds between frames
     */
    public void startStreaming(final StreamCallback callback, final long intervalMs) {
        if (imageReader == null) {
            Log.e(TAG, "Cannot start streaming - MediaProjection not started");
            return;
        }

        isStreaming = true;
        streamCallback = callback;

        backgroundHandler.post(new Runnable() {
            @Override
            public void run() {
                if (!isStreaming || imageReader == null) {
                    return;
                }
                Image image = imageReader.acquireLatestImage();
                if (image != null) {
                    try {
                        byte[] frame = imageToBytes(image);
                        if (frame != null && streamCallback != null) {
                            streamCallback.onFrame(frame);
                        }
                    } catch (Exception e) {
                        Log.e(TAG, "Error during streaming", e);
                    } finally {
                        image.close();
                    }
                }
                if (isStreaming) {
                    backgroundHandler.postDelayed(this, intervalMs);
                }
            }
        });

        Log.i(TAG, "Streaming started with interval: " + intervalMs + "ms");
    }

    /**
     * Stop continuous frame streaming.
     */
    public void stopStreaming() {
        isStreaming = false;
        streamCallback = null;
        Log.i(TAG, "Streaming stopped");
    }

    public boolean isProjectionActive() {
        return mediaProjection != null && imageReader != null;
    }

    public boolean isStreaming() {
        return isStreaming;
    }

    private byte[] imageToBytes(Image image) {
        Image.Plane[] planes = image.getPlanes();
        ByteBuffer buffer = planes[0].getBuffer();
        int pixelStride = planes[0].getPixelStride();
        int rowStride = planes[0].getRowStride();
        int rowPadding = rowStride - pixelStride * screenWidth;

        Bitmap bitmap = Bitmap.createBitmap(
                screenWidth + rowPadding / pixelStride,
                screenHeight,
                Bitmap.Config.ARGB_8888);
        bitmap.copyPixelsFromBuffer(buffer);

        // Crop padding if any
        if (rowPadding > 0) {
            Bitmap cropped = Bitmap.createBitmap(bitmap, 0, 0, screenWidth, screenHeight);
            bitmap.recycle();
            bitmap = cropped;
        }

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, baos);
        bitmap.recycle();
        return baos.toByteArray();
    }
}
