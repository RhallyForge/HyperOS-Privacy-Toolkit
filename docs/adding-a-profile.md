# Adding a compatibility profile

Profiles are evidence records, not optimistic compatibility claims. Add a writable profile only after testing on a physical device.

## Required evidence

Record without personal data:

- retail model and Android codename;
- Android and full MIUI/HyperOS version;
- region and UI locale;
- exact package names present on that build;
- exact labels and resource IDs used for navigation;
- initial state, action, final state and persistence after reopening;
- confirmation-dialog behavior;
- restore behavior or an explicit “manual only / unverified” limitation.

Do not include an ADB serial, local IP address, account name, filename, notification, pairing code, raw UI dump or unredacted screenshot.

## Maturity

- `verified`: the full before/action/after flow was reproduced on the exact match criteria.
- `experimental`: read-only or incomplete evidence; users must opt in with `--include-experimental`.
- unsupported behavior belongs in `unsupported`, not in a writable action.

## Match narrowly

Prefer exact model, codename, HyperOS prefix, locale and region. A firmware update or different language may change resource IDs and labels. Create a separate profile when the UI differs.

## Navigation rules

- Prefer Android intents, package names, resource IDs and exact labels.
- Use scroll-to-text before relative swipes.
- Never use fixed screen coordinates in a profile.
- Never guess an action when a label or control is missing.
- Read the switch before and after every touch.

## Tests

Add an offline profile-selection test and run:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

Device-derived logs remain local and must not be committed.
