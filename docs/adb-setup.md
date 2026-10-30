# ADB setup on Windows

## Official Platform-Tools

Download Android SDK Platform-Tools only from Android Developers:

<https://developer.android.com/tools/releases/platform-tools>

Extract the archive and either add `platform-tools` to `PATH` or pass the full `adb.exe` path with `--adb`.

## USB debugging

1. On the phone, open **Settings > About phone**.
2. Tap the OS/MIUI version seven times to unlock Developer options.
3. Open **Settings > Additional settings > Developer options**.
4. Enable **USB debugging**.
5. Connect a data-capable USB cable, unlock the phone and approve the RSA fingerprint.
6. Run `adb devices -l`. The state must be `device`, not `unauthorized` or `offline`.

USB debugging authorizes the ADB transport. It is separate from wireless debugging and from Xiaomi's additional input-injection control.

## Wireless debugging

Android 11 and later can pair ADB over Wi-Fi:

```powershell
adb pair PHONE_IP:PAIRING_PORT
adb connect PHONE_IP:ADB_PORT
adb devices -l
```

The pairing port and connection port can differ and may change. Never publish pairing codes, local IP addresses or ADB endpoints. The toolkit accepts an IP endpoint or an `_adb-tls-connect._tcp` mDNS name through `--serial` but does not save it in logs.

## USB debugging (Security settings)

On some Xiaomi/HyperOS builds, ADB shell commands work while UI input fails with:

```text
SecurityException: Injecting to another application requires INJECT_EVENTS permission
```

This does not mean ordinary USB debugging or wireless debugging is off. It means HyperOS has not granted the separate shell-input authorization.

Enable **USB debugging (Security settings)** in Developer options, then reconnect ADB. Some builds require a phone reboot before `persist.security.adbinput=1` and `adb shell input keyevent KEYCODE_HOME` take effect.

The toolkit does not bypass this protection. Keep the screen unlocked while using UI actions.

## Common states

- `unauthorized`: unlock the phone and approve the RSA prompt.
- `offline`: reconnect the cable/network and restart the ADB server.
- multiple entries for the same model: the same phone may appear through IP and mDNS; the toolkit deduplicates matching product/model/device entries.
- multiple distinct phones: pass `--serial` explicitly.
