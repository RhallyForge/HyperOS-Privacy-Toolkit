# HyperOS Privacy Toolkit

HyperOS Privacy Toolkit is a conservative Windows tool for inspecting and, only with explicit approval, changing verified advertising and optional-data settings on Xiaomi, Redmi and POCO devices.

It uses the official Android SDK Platform-Tools (`adb`) and UI Automator through `uiautomator2`. The default command is read-only analysis. It does not require root, an unlocked bootloader, flashing, package removal or a factory reset.

> **Alpha / device profiles required:** UI labels and flows change across device, region, language and firmware. Writable actions are exposed only by an exact compatibility profile. Unknown devices fall back to read-only detection.

## What is verified

The first verified profile is deliberately narrow:

- POCO F5 (`23049PCD8G`, codename `marble`)
- Android 15
- HyperOS `OS3.0.4.0` Global
- Italian UI (`it-IT`, region `IT`)

| Action | Status | Result on the tested device |
|---|---|---|
| Security — Receive suggestions | Verified | Toggle detected, disabled and re-read |
| Cleaner — Receive suggestions | Verified | Toggle detected, disabled and re-read |
| Downloads — Recommended content | Verified | Confirmation handled; toggle disabled; ad container absent in the observed screen |
| MSA authorization revocation | Verified apply | Official Xiaomi countdown confirmed; state persisted after reopening Settings |
| MSA automatic reactivation | Manual only | The UI path is documented, but automatic reactivation has not been tested |
| File Manager network audit | Experimental / read-only | Wi-Fi control was present but disabled by HyperOS |
| File Manager GMC ad sampling | Experimental / read-only | Detects the known ad activity; absence in a sample is never treated as proof |
| Disable MSA or Analytics with PackageManager | Unsupported | HyperOS returned `SecurityException: Cannot disable system packages` |

No compatibility is claimed for other models, firmware versions, regions or interface languages until a separate profile is tested.

## Safety model

- `analyze` is the default and does not change settings.
- `apply` changes exactly one named action.
- The action ID must be repeated with `--confirm`.
- MSA revocation also requires `--acknowledge-data-deletion` because Xiaomi warns that related server data may be deleted.
- Every action reads the switch before and after touching it.
- If a screen, label or control does not match the selected profile, the action fails without guessing.
- Runtime logs and screenshots are local and ignored by Git.
- Device serials and local IP addresses are not written to logs.

The toolkit never offers package uninstall, data/cache clearing, bootloader operations, root, flashing or bypasses of HyperOS protections.

## Requirements

- Windows 10 or 11
- Python 3.11 or newer
- Official [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools)
- A Xiaomi/Redmi/POCO device connected through authorized USB or wireless ADB
- An unlocked screen for UI analysis
- **USB debugging (Security settings)** when HyperOS otherwise rejects UI input with `INJECT_EVENTS`

## Install

```powershell
git clone <private-repository-url>
cd HyperOS-Privacy-Toolkit
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

Check ADB and compatibility without changing the phone:

```powershell
hyperos-privacy doctor
hyperos-privacy list-actions
hyperos-privacy analyze
```

If `adb` is not on `PATH`:

```powershell
hyperos-privacy --adb 'C:\path\to\platform-tools\adb.exe' doctor
```

When multiple distinct phones are connected, pass `--serial`. The value is used only for the current connection and is not saved in logs.

## Applying one verified action

First run analysis:

```powershell
hyperos-privacy analyze --action security-recommendations
```

Then explicitly authorize the same action ID:

```powershell
hyperos-privacy apply security-recommendations `
  --confirm security-recommendations
```

MSA authorization revocation has an additional acknowledgement:

```powershell
hyperos-privacy apply msa-authorization-revocation `
  --confirm msa-authorization-revocation `
  --acknowledge-data-deletion
```

This revokes Xiaomi's MSA authorization. It does **not** disable or uninstall `com.miui.msa.global`.

## Restoring a tool change

Automatic restoration is available only for actions whose reverse path was verified:

```powershell
hyperos-privacy restore runtime\logs\run-YYYYMMDD-HHMMSS-apply.json `
  --action security-recommendations `
  --confirm security-recommendations
```

MSA reactivation remains manual because the reverse automation has not been tested. See [technical findings](docs/technical-findings.md).

## PowerShell wrapper

Users who prefer PowerShell can run:

```powershell
.\tools\Invoke-HyperOSPrivacyToolkit.ps1 -Command doctor
.\tools\Invoke-HyperOSPrivacyToolkit.ps1 -Command analyze -Action security-recommendations
```

The wrapper still invokes the same Python engine and safety checks.

## Experimental File Manager ad sample

```powershell
hyperos-privacy sample-filemanager-ads --attempts 10 --include-experimental
```

The sampler records the foreground activity. A full screenshot is saved only when the known GMC advertising activity is in front; otherwise only the top toolbar is retained to avoid exposing filenames. Even ten clean launches do not prove that intermittent ads are gone.

## Privacy and limitations

The project does not inspect photos, messages, accounts or file contents. UI hierarchy dumps are used only on known settings screens. Raw device dumps, original logs and screenshots from development are not included.

Revoking MSA reduced the tested authorization state, but this project does not claim that all Xiaomi telemetry stops. Security, updates, diagnostics, cloud services and other components may continue necessary or optional network activity. No residual-telemetry claim is made without independent traffic evidence.

See:

- [ADB setup and INJECT_EVENTS](docs/adb-setup.md)
- [Compatibility matrix](docs/compatibility.md)
- [Technical findings](docs/technical-findings.md)
- [Safety and data handling](docs/safety-and-data-handling.md)
- [Adding a compatibility profile](docs/adding-a-profile.md)
- [Italian guide](README.it.md)

## Development

Offline tests do not require a connected phone:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

## License

MIT. `uiautomator2` and `adbutils` are MIT-licensed dependencies; Pillow uses the MIT-CMU license. Android SDK Platform-Tools are distributed separately by Google and are not bundled.
