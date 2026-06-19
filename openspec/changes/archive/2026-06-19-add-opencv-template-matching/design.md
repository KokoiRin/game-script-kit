# Design: OpenCV template matching

## Boundary

OpenCV belongs in the desktop adapter only. The engine continues to depend on
`ScreenImageLocator`, and script semantics continue to pass a template, optional
region, and `min_confidence`.

## Matching Algorithm

`PyAutoGuiScreenImageLocator` captures the current screen with `pyautogui`,
loads the template image, converts both images to RGB arrays, then runs
`cv2.matchTemplate(..., cv2.TM_CCOEFF_NORMED)`.

The adapter selects the best score with `cv2.minMaxLoc`:

- if the template is larger than the screenshot or selected region, return
  `None`;
- if the best score is lower than `min_confidence`, return `None`;
- otherwise return `ImageMatch(rect=..., confidence=best_score)`.

## UI Confidence

The local UI image-click action accepts a minimum confidence value. The browser
keeps a simple numeric input with default `0.8`; the HTTP adapter parses it and
the application use case validates it by constructing `ImageTarget`.

## Error Handling

Missing `pyautogui`, `cv2`, `numpy`, unreadable templates, and screenshot
failures are wrapped as setup/runtime errors from the adapter. A normal
low-confidence result is not an error.
