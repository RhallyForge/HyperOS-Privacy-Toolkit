# Technical findings

## DEFAULT is not DISABLED_USER

Android's package enabled-state codes are:

| Code | Meaning |
|---:|---|
| `0` | `DEFAULT` |
| `1` | `ENABLED` |
| `2` | `DISABLED` |
| `3` | `DISABLED_USER` |
| `4` | `DISABLED_UNTIL_USED` |

An early prototype incorrectly classified `enabled=0` as disabled. The toolkit now parses and tests this mapping explicitly. A package in DEFAULT state may still be enabled and running.

## HyperOS protects some system packages

On the verified POCO F5 build, both commands were rejected:

```text
pm disable-user --user 0 com.miui.msa.global
pm disable-user --user 0 com.miui.analytics
```

PackageManager returned `SecurityException: Cannot disable system packages`. The toolkit does not retry, bypass or offer these operations.

`pm default-state` was present and restored the original DEFAULT state during testing, but no package change occurred because the disable commands were rejected.

## MSA authorization is a different control

HyperOS exposes **Authorization & revocation** under the fingerprint/face/lock-screen settings area. Revoking `msa` there:

- uses Xiaomi's official UI;
- displays a countdown confirmation;
- warns that data collection stops and related server data may be deleted;
- changes the Xiaomi authorization switch;
- does not disable or uninstall `com.miui.msa.global` in PackageManager.

The tested switch remained off after closing and reopening Settings. Automatic reactivation has not been tested, so the toolkit reports a manual reverse procedure instead of pretending restoration is verified.

Reference supplied during development: <https://new.c.mi.com/global/post/1905750>

## Verified advertising switches

The following Italian UI controls were changed and re-read successfully:

- Security: `Ricevi suggerimenti`
- Cleaner: `Ricevi suggerimenti`
- Downloads: `Mostra i contenuti consigliati`

Downloads displayed a confirmation titled `Disattiva le fonti consigliate`. The toolkit accepts only that known flow and verifies the switch afterward.

## File Manager ads and GMC

The verified File Manager package was `com.mi.android.globalFileexplorer`. During a natural app launch, the foreground window was:

```text
com.mi.android.globalFileexplorer/
com.zeus.gmc.sdk.mobileads.columbus.ad.videoads.player.GMCAdActivity
```

The component belongs to the File Manager package. This disproved an earlier unsupported attribution of the overlay itself to MSA. It does not identify the network backend or prove that MSA has no indirect role.

The package also declared Google and Yandex mobile-ad initialization providers. No claim is made about which provider served a particular impression.

HyperOS exposed File Manager network controls for mobile data, Wi-Fi and background data. The Wi-Fi control was checked but disabled, so a complete per-app network block could not be applied through the built-in UI. A partial mobile/background block was not used as evidence while the phone was on Wi-Fi.

## Intermittent ads

The GMC overlay appeared in one controlled observation and failed to appear in many later cold launches, both before and after MSA authorization revocation. Therefore:

- an observed GMC activity is evidence that an ad was presented;
- no ad in five, ten or more launches is only “not observed in this sample”;
- it is not proof of permanent removal;
- comparisons need longer observation windows or privacy-preserving per-app network evidence.

## Residual telemetry remains open

This toolkit does not claim that MSA revocation or recommendation toggles stop all Xiaomi telemetry. Necessary security, update, account, cloud and diagnostics traffic may remain. Domain-only firewall/DNS logs can provide limited evidence but cannot always distinguish ads, telemetry and required services.

No HTTPS interception, CA installation or personal-content capture was used during development.
