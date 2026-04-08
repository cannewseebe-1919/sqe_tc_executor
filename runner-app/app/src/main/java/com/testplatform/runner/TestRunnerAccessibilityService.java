package com.testplatform.runner;

import android.accessibilityservice.AccessibilityService;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * AccessibilityService implementation for UI tree inspection.
 * Provides methods to get the current UI tree and find specific elements.
 */
public class TestRunnerAccessibilityService extends AccessibilityService {

    private static final String TAG = "RunnerA11yService";
    private static TestRunnerAccessibilityService instance;

    public static TestRunnerAccessibilityService getInstance() {
        return instance;
    }

    @Override
    public void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        Log.i(TAG, "Accessibility service connected");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // We don't need to react to events; we query the tree on demand.
    }

    @Override
    public void onInterrupt() {
        Log.w(TAG, "Accessibility service interrupted");
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        instance = null;
        Log.i(TAG, "Accessibility service destroyed");
    }

    /**
     * Get the full UI tree of the current screen as JSON.
     *
     * @return JSONObject representing the UI tree, or empty object if unavailable
     */
    public JSONObject getUITree() {
        AccessibilityNodeInfo rootNode = getRootInActiveWindow();
        if (rootNode == null) {
            Log.w(TAG, "Root node is null - cannot get UI tree");
            return new JSONObject();
        }
        try {
            return UITreeParser.parseTree(rootNode);
        } finally {
            rootNode.recycle();
        }
    }

    /**
     * Find elements matching the given criteria.
     *
     * @param text       text to match (can be null)
     * @param resourceId resource ID to match (can be null)
     * @param className  class name to match (can be null)
     * @return JSONArray of matching elements with their properties and coordinates
     */
    public JSONArray findElements(String text, String resourceId, String className) {
        AccessibilityNodeInfo rootNode = getRootInActiveWindow();
        if (rootNode == null) {
            Log.w(TAG, "Root node is null - cannot find elements");
            return new JSONArray();
        }
        try {
            return UITreeParser.findElements(rootNode, text, resourceId, className);
        } finally {
            rootNode.recycle();
        }
    }

    /**
     * Check if the accessibility service is currently active.
     */
    public static boolean isServiceActive() {
        return instance != null;
    }
}
