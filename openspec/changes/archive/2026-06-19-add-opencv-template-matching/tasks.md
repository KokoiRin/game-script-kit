## 1. Spec

- [x] 1.1 Add screen-image-matching delta for OpenCV-backed confidence scores.
- [x] 1.2 Add local-control-ui delta for configurable image confidence.

## 2. Implementation

- [x] 2.1 Add OpenCV runtime dependency.
- [x] 2.2 Replace desktop image locator internals with screenshot + OpenCV matching.
- [x] 2.3 Propagate image confidence through local UI HTTP/application path.
- [x] 2.4 Update README usage notes.

## 3. Verification

- [x] 3.1 Run targeted adapter/UI tests.
- [x] 3.2 Run full pytest suite.
- [x] 3.3 Run OpenSpec strict validation.
- [x] 3.4 Run a real local smoke match against the current screen.
