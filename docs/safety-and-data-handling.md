# Safety and data handling

## Non-goals

The toolkit is not a general debloater, RAM optimizer or package-removal utility. It does not offer:

- root or bootloader operations;
- firmware flashing or factory reset;
- package uninstall;
- app data or cache clearing;
- changes to launcher, telephony, payments, accounts, location, system updates or Google Play services;
- protection bypasses.

## Explicit authorization

Every writable action requires the exact action ID through `--confirm`. MSA revocation requires a second acknowledgement because Xiaomi's dialog mentions server-side data deletion.

The program never treats analysis, a previous run or a compatible profile as authorization to modify the device.

## Logs

Runtime logs contain:

- public device characteristics needed for compatibility;
- selected profile;
- action ID;
- initial and final switch states;
- verification and restore status.

They do not contain the ADB serial or local IP address. A short one-way hash is used only to correlate local runs. The entire `runtime/` directory is ignored by Git.

## Screenshots and UI hierarchy

Full UI dumps may contain filenames, account names or notifications. Public diagnostic commands therefore avoid generic hierarchy printing.

The File Manager sampler saves:

- a full screenshot only when the known full-screen advertising activity is in front; or
- a crop of the top toolbar when no ad is present.

Runtime evidence is ignored by Git and must be reviewed manually before sharing.

## Repository hygiene

Before publishing:

1. Run offline tests.
2. Search for local IP addresses, pairing codes, device serials, tokens and private keys.
3. Inspect `git status` and the exact staged diff.
4. Verify that `runtime/`, logs, screenshots, dumps and virtual environments are untracked.
5. Create the GitHub repository as private first.
