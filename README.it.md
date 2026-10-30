# HyperOS Privacy Toolkit — guida italiana

HyperOS Privacy Toolkit analizza e, solo dopo autorizzazione esplicita, modifica impostazioni pubblicitarie e di raccolta dati facoltativa verificate su dispositivi Xiaomi, Redmi e POCO.

Usa gli Android SDK Platform-Tools ufficiali e UI Automator. La modalità predefinita è `analyze` e non modifica il telefono. Non richiede root, bootloader sbloccato, flash, disinstallazioni o cancellazione dati.

## Compatibilità realmente verificata

L'unico profilo scrivibile attuale è:

- POCO F5 `23049PCD8G` (`marble`)
- Android 15
- HyperOS `OS3.0.4.0` globale
- interfaccia italiana, regione Italia

Su altri dispositivi il programma effettua il rilevamento e seleziona il profilo generico in sola lettura. Non tenta tocchi basati su nomi o percorsi non verificati.

### Funzioni verificate

- Disattivazione “Ricevi suggerimenti” in Sicurezza.
- Disattivazione “Ricevi suggerimenti” in Pulizia.
- Disattivazione “Mostra i contenuti consigliati” in Download, inclusa la conferma.
- Revoca ufficiale dell'autorizzazione MSA, con conto alla rovescia e verifica dopo la riapertura delle Impostazioni.
- Log prima/dopo e ripristino automatico per i tre interruttori pubblicitari.

### Funzioni sperimentali o incomplete

- Controllo rete di Gestione File: il Wi-Fi era visibile ma non modificabile.
- Campionamento degli annunci GMC di Gestione File: gli annunci sono intermittenti; l'assenza in alcune aperture non prova la risoluzione.
- Riattivazione MSA: percorso manuale documentato, automazione inversa non ancora verificata.
- Telemetria residua: non misurata in modo sufficiente per dichiararla disattivata.

La disabilitazione PackageManager di MSA e Analytics non è offerta: HyperOS ha rifiutato entrambi i comandi con `Cannot disable system packages`.

## Installazione

1. Installa Python 3.11 o successivo.
2. Installa gli [SDK Platform-Tools ufficiali](https://developer.android.com/tools/releases/platform-tools).
3. Clona il repository e prepara l'ambiente:

```powershell
cd HyperOS-Privacy-Toolkit
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Primo controllo sicuro

```powershell
hyperos-privacy doctor
hyperos-privacy list-actions
hyperos-privacy analyze
```

Se ADB non è nel `PATH`:

```powershell
hyperos-privacy --adb 'C:\percorso\platform-tools\adb.exe' doctor
```

Il programma rileva automaticamente USB o ADB wireless. Se lo stesso telefono compare sia come IP sia tramite mDNS, lo deduplica. Con più telefoni distinti richiede `--serial`.

## Applicare una singola modifica

Analizza prima l'azione:

```powershell
hyperos-privacy analyze --action downloads-recommended-content
```

Poi ripeti esattamente il suo ID nella conferma:

```powershell
hyperos-privacy apply downloads-recommended-content `
  --confirm downloads-recommended-content
```

Per la revoca MSA serve anche confermare di aver letto l'avviso Xiaomi sulla possibile eliminazione dei dati server:

```powershell
hyperos-privacy apply msa-authorization-revocation `
  --confirm msa-authorization-revocation `
  --acknowledge-data-deletion
```

La revoca MSA non disabilita il package: `com.miui.msa.global` resta installato e può rimanere nello stato PackageManager DEFAULT.

## Ripristino

Le modifiche a Sicurezza, Pulizia e Download possono essere ripristinate usando il log creato dal tool:

```powershell
hyperos-privacy restore runtime\logs\run-YYYYMMDD-HHMMSS-apply.json `
  --action security-recommendations `
  --confirm security-recommendations
```

Per riattivare manualmente MSA:

1. Apri Impostazioni e cerca “Autorizzazioni e revoche”.
2. Apri il risultato sotto “Impronte digitali, dati del viso e blocco schermo”.
3. Attiva esclusivamente `msa`.
4. Riapri la schermata e verifica che l'interruttore sia attivo.

## Debug USB e INJECT_EVENTS

Il debug wireless, il Debug USB normale e “Debug USB (impostazioni di sicurezza)” sono controlli distinti. ADB può collegarsi correttamente ma HyperOS può rifiutare i tocchi con un errore `INJECT_EVENTS`. In quel caso è necessario abilitare “Debug USB (impostazioni di sicurezza)” nelle Opzioni sviluppatore e riconnettere o riavviare ADB; il toolkit non tenta bypass.

Consulta [la procedura ADB completa](docs/adb-setup.md).

## Protezione dei dati

- Nessun file personale viene letto o trasferito.
- Log, screenshot e dump runtime sono esclusi da Git.
- Seriali ADB e IP locali non vengono scritti nei log.
- Gli screenshot sperimentali di Gestione File sono completi solo quando un overlay pubblicitario copre l'interfaccia; altrimenti viene conservata soltanto la barra superiore.
- Se una schermata non corrisponde al profilo, il programma si ferma senza indovinare.

## Test offline

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

Per dettagli e limiti consulta [compatibilità](docs/compatibility.md), [scoperte tecniche](docs/technical-findings.md) e [sicurezza](docs/safety-and-data-handling.md).
