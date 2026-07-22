# Windows Porting Plan

Last updated: 2026-07-22

## Goal

Bring the application to a usable Windows parity level for packaging, launch, proxying, session auth, and account runtime behavior.

## Done

- `constants.py` no longer hardcodes Linux-only paths for packaged runtime.
- `process_manager.py` no longer exports `QT_QPA_PLATFORM=xcb` on Windows.
- `process_manager.py` now forwards `device_name`, `fake_vendor`, and `fake_model` through environment variables on Windows.
- `process_manager.py` now guards `firejail` and `unshare` behind non-Windows checks.
- `proxy_manager.py` now resolves `gost` from `SHADOWGRAM_GOST_BIN`, bundled paths, and `PATH`.
- `base_module.py` now uses the shared `gost` resolver.
- `build_windows.bat` now copies `gost.exe` into the output bundle when present.

## Remaining Work

### 1. Runtime fingerprint parity

Status: complete

- Find the Windows runtime entry points that should consume `SHADOWGRAM_DEVICE_NAME`, `SHADOWGRAM_FAKE_VENDOR`, and `SHADOWGRAM_FAKE_MODEL`.
- Wire those values into the effective client fingerprint instead of only exporting them into the child process environment.
- Done: `src/core/auth.py` now applies runtime overrides through `src/core/managers/runtime_hw_manager.py` before creating Telethon and Hydrogram auth clients.
- Done: `src/core/managers/neuro_engine.py` and `src/ai_agents/ai_runner.py` now merge runtime `SHADOWGRAM_*` overrides into the hardware profile before creating Hydrogram clients.
- Done: `src/core/base_module.py` and `src/modules/session_checker.py` now apply the same runtime override helper before creating client instances from saved session data.
- Done: `src/services/mass_session_service.py` now applies the same runtime override helper in its direct Hydrogram client path instead of using only `device_name`.
- Verified by compile and residual grep that the known Telethon/Hydrogram auth and long-running runtime paths now use the same effective device metadata layer on Windows.

### 2. Bundled binary and packaging parity

Status: in progress

- Done: canonical Windows repo and bundle location for `gost.exe` is now `resources/bin/windows/gost.exe`.
- Done: `src/core/managers/proxy_manager.py` now prioritizes the canonical bundled Windows path before fallback locations.
- Done: `build_windows.bat` now treats `resources/bin/windows/gost.exe` as the single bundle copy source instead of supporting a second `bin/gost.exe` path.
- Done: `build_windows.bat` now calls `scripts/ensure_gost_windows.ps1` to auto-download pinned upstream `go-gost/gost` release `v3.2.6` as `gost_3.2.6_windows_amd64.zip`, verify it against the release `checksums.txt`, and extract `gost.exe` into `resources/bin/windows/gost.exe` when missing.
- Verify the Windows build includes every required external binary and runtime resource.
- Check PyInstaller or bundle settings for hidden imports and Windows-only assets.

### 3. Windows process/runtime behavior

Status: pending

- Audit subprocess spawning, process termination, and detached/background behavior on Windows.
- Replace any remaining Linux-only command assumptions in critical runtime paths.
- Verify log, temp, and working-directory behavior under packaged Windows execution.

### 4. File system and desktop integration

Status: pending

- Audit path handling, file opening, and explorer integration for Windows-specific edge cases.
- Verify writable directories, portable mode behavior, and resource lookup in packaged builds.

### 5. Validation matrix

Status: pending

- Define a repeatable Windows smoke test for launch, account add, proxy start, session auth, and account run.
- Record known limitations that remain Linux-only by design.

## Working Rules

- Only treat parity as complete when the Windows path actually consumes the same metadata, not when env vars are merely exported.
- Keep Linux-specific isolation features optional and guarded; do not let them block Windows runtime.
- Update this file after each completed step so it remains the source of truth.

## Next Step

Run `build_windows.bat` on a Windows host and verify that the pinned `gost.exe` download, checksum validation, bundle copy, and application launch all succeed.
