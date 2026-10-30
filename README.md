# HyperOS Privacy Toolkit

**Less advertising. More control over your Xiaomi, Redmi or POCO phone.**

A free, open-source project that helps identify and turn off selected advertising recommendations and optional data-sharing settings on supported HyperOS devices. No root or bootloader unlock required.

> **Early version — not a one-click cleaner yet.** Today this project is a command-line tool for Windows. A beginner-friendly graphical application is a goal, not an existing feature.

## What does it actually do?

| Feature | Status |
|---|---|
| Turn off suggestions in Security | Tested |
| Turn off suggestions in Cleaner | Tested |
| Turn off recommended content in Downloads | Tested |
| Revoke Xiaomi's MSA advertising authorization | Tested, extra warning required |
| Remove all File Manager ads | **Not proven** |
| Stop all Xiaomi telemetry | **Not proven** |

The tool checks the current setting, asks before changing it, and checks the result. Some actions can be restored automatically. MSA reauthorization is documented but not yet automated.

## Does my phone work?

**Tested:** POCO F5 (23049PCD8G / marble), Android 15, HyperOS OS3.0.4.0 Global, Italian interface.

**Other Xiaomi, Redmi and POCO devices:** detection only for now. The tool will **not** guess where to tap or apply untested changes.

## How do I use it?

The current version requires a Windows computer and some setup. If you're not comfortable with terminals, **we recommend waiting for a guided desktop version**.

1. Install [Python 3.11+](https://www.python.org/downloads/) and the official [Android Platform-Tools](https://developer.android.com/tools/releases/platform-tools).
2. Enable authorized USB or wireless debugging on your phone and connect it to the PC.
3. Open PowerShell in the downloaded project directory and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
hyperos-privacy doctor
hyperos-privacy analyze
```

These commands only check the connection and analyze the device; they do **not** change your phone.

For individual changes, confirmation, restoration and troubleshooting, see the [Italian guide](README.it.md) or the [technical instructions](docs/adb-setup.md).

## Safety first

- No root, factory reset, package removal or firmware changes.
- No automatic changes on unsupported phone profiles.
- Changes require explicit confirmation.
- No claim that all advertising or tracking disappears.
- Local logs and screenshots are excluded from the repository.
- Xiaomi may require **USB debugging (Security settings)** to allow automation.

## Project status and what's next

This is an experimental project, built and tested initially on one POCO F5. The next major improvement is a **simple Windows interface**: connect the device, review available changes and approve them with clear explanations.

Read the [technical findings](docs/technical-findings.md), [compatibility details](docs/compatibility.md), [safety policy](docs/safety-and-data-handling.md), or [contribution guide](CONTRIBUTING.md).

[Leggi in italiano](README.it.md) · [MIT License](LICENSE)
