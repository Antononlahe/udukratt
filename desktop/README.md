# Udukratt desktop (Tauri v2)

A desktop wrapper around the webapp, with the same UI and the same bundled 10 MB model. It runs fully offline:
- No network permissions: only `core:default` and `dialog:allow-save`.
- No http, shell or fs plugins.
- A strict CSP: `default-src 'self'`, and `connect-src` limited to Tauri IPC.

Features: drag-and-drop or Open file…, Redact, and Save redacted file…
- Supported formats: .txt .md .csv .json .xml .yaml .html .log .sql, plus .docx (text only, converted in Rust). PDF isn't supported.

Build:
```
gh release download v0.1 -p model_q4.onnx -D ../webapp/model
npm ci && npx tauri build --bundles appimage
```
Headless smoke test:
```
UDUKRATT_SMOKE_IN=in.yaml UDUKRATT_SAVE_TO=out.yaml xvfb-run -a ./Udukratt_*.AppImage --appimage-extract-and-run
```
