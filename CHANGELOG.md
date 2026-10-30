# Changelog

All notable changes to this project will be documented here.

## 0.1.0 — 2026-10-30

### Added

- Automatic discovery of official ADB Platform-Tools and connected USB/wireless devices.
- Deduplication when one phone appears through multiple wireless endpoints or USB plus wireless.
- MIUI/HyperOS, build, region, locale and current-user detection.
- Exact compatibility profiles with a generic read-only fallback.
- Read-only analysis as the default command.
- Verified POCO F5 actions for Security, Cleaner, Downloads and MSA authorization revocation.
- Explicit confirmation and MSA server-data-deletion acknowledgement guards.
- Before/after verification, local redacted logs and verified restore for supported toggles.
- Experimental privacy-safe File Manager GMC ad sampling and network-control audit.
- Offline unit tests and English/Italian documentation.

### Corrected

- Package state `enabled=0` is now correctly reported as DEFAULT, not DISABLED_USER.
- MSA overlay attribution is no longer assumed; the observed overlay activity belonged to File Manager's embedded GMC SDK.

### Known limitations

- Only one POCO F5 / HyperOS 3 Global / Italian UI profile has writable actions.
- MSA automatic reactivation is not verified.
- File Manager ads are intermittent and cannot be declared removed from short samples.
- Residual Xiaomi telemetry is not fully measured.
