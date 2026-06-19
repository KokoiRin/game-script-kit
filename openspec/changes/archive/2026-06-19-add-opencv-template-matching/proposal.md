# Change: Add OpenCV template matching

## Why

The current desktop image locator depends on `pyautogui.locateOnScreen`.
Even after OpenCV is installed, that path does not expose the actual match score
and failed to find a high-confidence template in the local smoke scenario.

## What Changes

- Declare OpenCV as a runtime dependency for desktop image matching.
- Implement `PyAutoGuiScreenImageLocator` using `pyautogui.screenshot` plus
  `cv2.matchTemplate` so it returns the actual best match confidence.
- Treat matches below `min_confidence` as not found.
- Allow the local UI image-click path to pass a configurable minimum confidence.

## Impact

- Affects only the desktop adapter and local UI/application entry path.
- Keeps `ScreenImageLocator`, `ImageExists`, and `ImageTarget` platform-neutral.
- Adds tests for OpenCV-backed matching and UI confidence propagation.
