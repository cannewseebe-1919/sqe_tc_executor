package com.testplatform.runner;

import android.graphics.Rect;
import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Parses AccessibilityNodeInfo tree into JSON representation.
 * Each node contains: class, text, resource_id, content_desc, bounds, clickable, enabled, etc.
 */
public class UITreeParser {

    private static final String TAG = "UITreeParser";

    /**
     * Parse the entire UI tree starting from the root node.
     *
     * @param rootNode the root AccessibilityNodeInfo
     * @return JSON representation of the UI tree
     */
    public static JSONObject parseTree(AccessibilityNodeInfo rootNode) {
        if (rootNode == null) {
            Log.w(TAG, "Root node is null");
            return new JSONObject();
        }
        try {
            return parseNode(rootNode, 0);
        } catch (JSONException e) {
            Log.e(TAG, "Error parsing UI tree", e);
            return new JSONObject();
        }
    }

    private static JSONObject parseNode(AccessibilityNodeInfo node, int depth) throws JSONException {
        if (node == null) {
            return null;
        }

        JSONObject obj = new JSONObject();

        // Class name
        CharSequence className = node.getClassName();
        obj.put("class", className != null ? className.toString() : "");

        // Text
        CharSequence text = node.getText();
        obj.put("text", text != null ? text.toString() : "");

        // Resource ID
        CharSequence resourceId = node.getViewIdResourceName();
        obj.put("resource_id", resourceId != null ? resourceId.toString() : "");

        // Content description
        CharSequence contentDesc = node.getContentDescription();
        obj.put("content_desc", contentDesc != null ? contentDesc.toString() : "");

        // Bounds
        Rect boundsInScreen = new Rect();
        node.getBoundsInScreen(boundsInScreen);
        JSONObject bounds = new JSONObject();
        bounds.put("left", boundsInScreen.left);
        bounds.put("top", boundsInScreen.top);
        bounds.put("right", boundsInScreen.right);
        bounds.put("bottom", boundsInScreen.bottom);
        bounds.put("center_x", boundsInScreen.centerX());
        bounds.put("center_y", boundsInScreen.centerY());
        obj.put("bounds", bounds);

        // Properties
        obj.put("clickable", node.isClickable());
        obj.put("enabled", node.isEnabled());
        obj.put("focusable", node.isFocusable());
        obj.put("focused", node.isFocused());
        obj.put("scrollable", node.isScrollable());
        obj.put("selected", node.isSelected());
        obj.put("checkable", node.isCheckable());
        obj.put("checked", node.isChecked());
        obj.put("visible_to_user", node.isVisibleToUser());
        obj.put("long_clickable", node.isLongClickable());
        obj.put("editable", node.isEditable());
        obj.put("depth", depth);

        // Package name
        CharSequence packageName = node.getPackageName();
        obj.put("package", packageName != null ? packageName.toString() : "");

        // Children
        int childCount = node.getChildCount();
        if (childCount > 0) {
            JSONArray children = new JSONArray();
            for (int i = 0; i < childCount; i++) {
                AccessibilityNodeInfo child = node.getChild(i);
                if (child != null) {
                    JSONObject childObj = parseNode(child, depth + 1);
                    if (childObj != null) {
                        children.put(childObj);
                    }
                    child.recycle();
                }
            }
            obj.put("children", children);
        }

        return obj;
    }

    /**
     * Find elements matching the given criteria.
     *
     * @param rootNode    the root node to search from
     * @param text        text to match (nullable)
     * @param resourceId  resource ID to match (nullable)
     * @param className   class name to match (nullable)
     * @return JSONArray of matching elements
     */
    public static JSONArray findElements(AccessibilityNodeInfo rootNode,
                                         String text, String resourceId, String className) {
        JSONArray results = new JSONArray();
        if (rootNode == null) {
            return results;
        }
        try {
            findElementsRecursive(rootNode, text, resourceId, className, results);
        } catch (JSONException e) {
            Log.e(TAG, "Error finding elements", e);
        }
        return results;
    }

    private static void findElementsRecursive(AccessibilityNodeInfo node,
                                               String text, String resourceId, String className,
                                               JSONArray results) throws JSONException {
        if (node == null) {
            return;
        }

        boolean matches = true;

        if (text != null && !text.isEmpty()) {
            CharSequence nodeText = node.getText();
            CharSequence nodeDesc = node.getContentDescription();
            String nodeTextStr = nodeText != null ? nodeText.toString() : "";
            String nodeDescStr = nodeDesc != null ? nodeDesc.toString() : "";
            if (!nodeTextStr.contains(text) && !nodeDescStr.contains(text)) {
                matches = false;
            }
        }

        if (resourceId != null && !resourceId.isEmpty()) {
            CharSequence nodeResId = node.getViewIdResourceName();
            String nodeResIdStr = nodeResId != null ? nodeResId.toString() : "";
            if (!nodeResIdStr.contains(resourceId)) {
                matches = false;
            }
        }

        if (className != null && !className.isEmpty()) {
            CharSequence nodeClass = node.getClassName();
            String nodeClassStr = nodeClass != null ? nodeClass.toString() : "";
            if (!nodeClassStr.contains(className)) {
                matches = false;
            }
        }

        if (matches) {
            // Build a simplified result for the matched node
            Rect boundsInScreen = new Rect();
            node.getBoundsInScreen(boundsInScreen);

            JSONObject element = new JSONObject();
            CharSequence cls = node.getClassName();
            element.put("class", cls != null ? cls.toString() : "");
            CharSequence t = node.getText();
            element.put("text", t != null ? t.toString() : "");
            CharSequence rid = node.getViewIdResourceName();
            element.put("resource_id", rid != null ? rid.toString() : "");
            CharSequence cd = node.getContentDescription();
            element.put("content_desc", cd != null ? cd.toString() : "");

            JSONObject bounds = new JSONObject();
            bounds.put("left", boundsInScreen.left);
            bounds.put("top", boundsInScreen.top);
            bounds.put("right", boundsInScreen.right);
            bounds.put("bottom", boundsInScreen.bottom);
            bounds.put("center_x", boundsInScreen.centerX());
            bounds.put("center_y", boundsInScreen.centerY());
            element.put("bounds", bounds);

            element.put("clickable", node.isClickable());
            element.put("enabled", node.isEnabled());
            element.put("visible_to_user", node.isVisibleToUser());

            results.put(element);
        }

        // Recurse into children
        int childCount = node.getChildCount();
        for (int i = 0; i < childCount; i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child != null) {
                findElementsRecursive(child, text, resourceId, className, results);
                child.recycle();
            }
        }
    }
}
