## 1. Application Interfaces

- [x] 1.1 Add application use case for listing scripts and running a named script with normalized output.
- [x] 1.2 Add application use case for running whitelisted test tasks and rejecting unknown task names.
- [x] 1.3 Cover application use cases with behavior tests.

## 2. Local UI Entrypoint

- [x] 2.1 Add lightweight local UI HTTP server with `GET /`, `GET /api/scripts`, `POST /api/run-script`, and `POST /api/run-tests`.
- [x] 2.2 Add HTML page with script selection, dry-run controls, run output, and fixed test button.
- [x] 2.3 Cover HTTP API behavior with end-to-end style tests using local server requests.

## 3. CLI Integration

- [x] 3.1 Add `star ui` CLI command with host, port, and `--no-open` options.
- [x] 3.2 Ensure importing or showing CLI help does not start UI server or platform adapters.
- [x] 3.3 Cover `star ui` CLI argument wiring with tests.

## 4. Documentation And Validation

- [x] 4.1 Update README with UI usage and end-to-end verification commands.
- [x] 4.2 Run focused tests for new application/UI/CLI behavior.
- [x] 4.3 Run full pytest suite, OpenSpec validation, and diff whitespace check.
- [x] 4.4 Run Warden review and archive the OpenSpec change if the review passes.
