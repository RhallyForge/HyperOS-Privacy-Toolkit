# Compatibility

## Verified profile

| Field | Verified value |
|---|---|
| Device | POCO F5 |
| Model | `23049PCD8G` |
| Codename | `marble` |
| Android | 15 |
| Firmware | HyperOS `OS3.0.4.0` Global |
| Locale / region | `it-IT` / `IT` |
| ADB | Wireless and standard shell commands |
| UI input | Required Xiaomi “USB debugging (Security settings)” |

This profile is based on one physical device. It does not imply compatibility with other POCO F5 regions, languages or firmware updates.

## Generic profile

Other Xiaomi, Redmi and POCO devices receive the `generic-xiaomi-read-only` profile. It provides:

- automatic ADB transport selection;
- model, codename, Android, MIUI/HyperOS, region and current-user detection;
- compatibility reporting.

It provides no writable UI actions. A new profile must document the exact model, build, locale, labels, resource IDs, initial state, resulting state and restore behavior.

## Action status

| Action | Maturity | Notes |
|---|---|---|
| Security recommendations | Verified | Italian label and Security Center resource ID |
| Cleaner recommendations | Verified | Opened through Security settings |
| Downloads recommended content | Verified | Handles the observed confirmation dialog |
| MSA authorization revocation | Verified apply | Persistence verified; automatic reverse path not tested |
| File Manager network controls | Experimental read-only | Wi-Fi switch disabled on tested build |
| File Manager GMC sampling | Experimental read-only | Activity detection is precise; statistical conclusion is not |
| Themes / GetApps / Music changes | Unsupported | Consent or permission boundaries prevented safe automation |
| Google usage diagnostics | Unsupported | Asynchronous state was inconsistent across reopenings |
| Package disable for MSA/Analytics | Unsupported | HyperOS rejected `pm disable-user` |
