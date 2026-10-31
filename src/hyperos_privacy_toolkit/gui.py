"""Windows desktop interface. The verified CLI engine remains authoritative."""

from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from typing import Any

from .adb import AdbClient, find_adb, select_device
from .logging import RunLog
from .operations import ActionExecutor
from .profiles import default_profiles_dir, load_profiles, select_profile
from .safety import opaque_device_reference

BG = "#0c1425"
PANEL = "#16223a"
BORDER = "#273956"
TEXT = "#eaf2ff"
MUTED = "#a5b5cd"
BLUE = "#348ef5"
GREEN = "#4adeac"
YELLOW = "#f7ca76"
RED = "#fa7c89"

LABELS = {
    "security-recommendations": (
        "Suggerimenti in Sicurezza",
        "Riduce i suggerimenti promozionali nell'app Sicurezza.",
    ),
    "cleaner-recommendations": (
        "Suggerimenti in Pulizia",
        "Riduce i consigli commerciali nella funzione Pulizia.",
    ),
    "downloads-recommended-content": (
        "Contenuti consigliati in Download",
        "Disattiva i contenuti promozionali nell'app Download.",
    ),
    "msa-authorization-revocation": (
        "Autorizzazione pubblicitaria Xiaomi (MSA)",
        "Revoca il consenso MSA tramite la schermata ufficiale Xiaomi.",
    ),
    "filemanager-network-audit": (
        "Controlli rete di Gestione File",
        "Sola analisi: il blocco Wi-Fi non è disponibile sul dispositivo testato.",
    ),
}


def endpoint_is_valid(value: str) -> bool:
    """Restrict pairing and connection targets to an IPv4 address and TCP port."""
    import ipaddress

    match = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})", value.strip())
    if not match:
        return False
    try:
        ipaddress.IPv4Address(match.group(1))
    except ipaddress.AddressValueError:
        return False
    port = int(match.group(2))
    return 1 <= port <= 65535


class PrivacyApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("HyperOS Privacy Toolkit")
        self.configure(bg=BG)
        self.geometry("990x780")
        self.minsize(750, 620)
        self.option_add("*Font", "Segoe UI 10")
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.busy = False
        self.connection: tuple[Any, Any, Any, Any] | None = None
        self.rows: dict[str, dict[str, Any]] = {}
        self.results: dict[str, Any] = {}
        self.adb_path = tk.StringVar(value="")
        self.notice = tk.StringVar(value="Collega il telefono e premi 'Trova telefono'.")
        self.device_text = tk.StringVar(value="Nessun telefono rilevato")
        self.profile_text = tk.StringVar(value="Nessun profilo verificato")
        self._render()
        self.after(100, self._poll_queue)

    def _label(self, parent: tk.Widget, text: str, *,
               size: int = 11, color: str = TEXT, bold: bool = False,
               **kwargs: Any) -> tk.Label:
        return tk.Label(
            parent, text=text, bg=parent.cget("bg"), fg=color,
            font=("Segoe UI", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _button(self, parent: tk.Widget, text: str, command: Any,
                color: str = BLUE) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, cursor="hand2",
            bg=color, fg="#ffffff", activebackground="#1f67bc",
            activeforeground="#ffffff", relief="flat", bd=0,
            padx=13, pady=9, font=("Segoe UI", 10, "bold"),
            disabledforeground="#8d9aaf",
        )

    def _render(self) -> None:
        header = tk.Frame(self, bg=BG, padx=32, pady=20)
        header.pack(fill="x")
        self._label(header, "HyperOS  Privacy Toolkit", size=26, bold=True).pack(anchor="w")
        self._label(
            header, "Meno pubblicità, più controllo. Nessun root.",
            color=MUTED, size=12,
        ).pack(anchor="w", pady=(5, 0))
        self._label(
            header,
            "VERSIONE SPERIMENTALE  •  Solo le impostazioni già verificate possono essere cambiate",
            color=YELLOW, size=9,
        ).pack(anchor="w", pady=(13, 0))

        connect = tk.Frame(self, bg=PANEL, padx=18, pady=14, highlightbackground=BORDER, highlightthickness=1)
        connect.pack(fill="x", padx=32, pady=(0, 14))
        self._label(connect, "1   Collega il telefono", bold=True, size=14).pack(anchor="w")
        self._label(connect, textvariable=self.device_text, size=11).pack(anchor="w", pady=(6, 0))
        self._label(connect, textvariable=self.profile_text, color=MUTED, size=9).pack(anchor="w", pady=(2, 9))

        toolbar = tk.Frame(connect, bg=PANEL)
        toolbar.pack(fill="x")
        self.find_button = self._button(toolbar, "Trova telefono", self.inspect)
        self.find_button.pack(side="left", padx=(0, 7))
        self.wifi_button = self._button(toolbar, "Cerca tramite Wi-Fi", self.find_wifi, "#234b79")
        self.wifi_button.pack(side="left", padx=(0, 7))
        self.pair_button = self._button(toolbar, "Associa Wi-Fi", self.pair_wifi, "#234b79")
        self.pair_button.pack(side="left")
        pathrow = tk.Frame(connect, bg=PANEL)
        pathrow.pack(fill="x", pady=(12, 0))
        self._label(pathrow, "ADB (opzionale):", size=9, color=MUTED).pack(side="left", padx=(0, 7))
        self.adb_entry = tk.Entry(pathrow, textvariable=self.adb_path, font=("Consolas", 9),
                                  bg="#0b1830", fg=TEXT, insertbackground=TEXT,
                                  relief="flat", highlightthickness=1, highlightbackground=BORDER)
        self.adb_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self._button(pathrow, "Sfoglia", self.choose_adb, "#234b79").pack(side="left", padx=(8, 0))

        section = tk.Frame(self, bg=BG, padx=32)
        section.pack(fill="x", pady=(5, 10))
        self._label(section, "2   Controlla le impostazioni", bold=True, size=16).pack(side="left")
        self.analyze_button = self._button(section, "Analizza tutto", self.analyze_all)
        self.analyze_button.pack(side="right")

        center = tk.Frame(self, bg=BG)
        center.pack(fill="both", expand=True, padx=32)
        self.canvas = tk.Canvas(center, bg=BG, borderwidth=0, highlightthickness=0)
        scroll = tk.Scrollbar(center, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.list_frame = tk.Frame(self.canvas, bg=BG)
        self.window_item = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfig(self.window_item, width=event.width))
        self._label(self.list_frame, "Connetti un dispositivo per vedere le opzioni disponibili.", color=MUTED).pack(
            anchor="w", pady=20,
        )

        footer = tk.Frame(self, bg=PANEL, padx=32, pady=13)
        footer.pack(fill="x", side="bottom")
        self._label(footer, textvariable=self.notice, size=10, color=TEXT, wraplength=870,
                    justify="left").pack(anchor="w")
        self._label(
            footer, "Le modifiche sono sempre singole e richiedono una conferma. "
                    "Non disinstalla applicazioni e non modifica il sistema operativo.",
            size=9, color=MUTED, wraplength=870, justify="left",
        ).pack(anchor="w", pady=(6, 0))

    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self.busy = busy
        for button in (self.find_button, self.wifi_button, self.pair_button, self.analyze_button):
            button.configure(state="disabled" if busy else "normal")
        for item in self.rows.values():
            for name in ("analyze_button", "apply_button", "restore_button"):
                item[name].configure(state="disabled" if busy else item["enabled"][name])
        if msg:
            self.notice.set(msg)

    def _background(self, task: Any, title: str) -> None:
        if self.busy:
            return
        self._set_busy(True, title)

        def run() -> None:
            try:
                task()
            except Exception as exc:
                self.messages.put(("error", str(exc)))
            finally:
                self.messages.put(("idle", None))

        threading.Thread(target=run, daemon=True).start()

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == "connected":
                    self._show_connection(*value)
                elif kind == "result":
                    self._show_result(value)
                elif kind == "notice":
                    self.notice.set(str(value))
                elif kind == "error":
                    self.notice.set("Operazione non riuscita: " + str(value))
                    messagebox.showerror("Operazione non riuscita", str(value))
                elif kind == "idle":
                    self._set_busy(False)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def choose_adb(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleziona adb.exe", filetypes=[("Android Debug Bridge", "adb.exe"), ("Tutti i file", "*.*")],
        )
        if path:
            self.adb_path.set(path)

    def _adb(self) -> Path:
        return find_adb(self.adb_path.get().strip() or None)

    def _discover(self) -> tuple[Any, Any, Any, Any]:
        adb = self._adb()
        discovery = AdbClient(adb)
        connected = select_device(discovery.list_devices())
        client = AdbClient(adb, connected.serial)
        info = client.detect_device_info(connected.transport)
        profile = select_profile(load_profiles(default_profiles_dir()), info)
        return adb, connected, info, profile

    def inspect(self) -> None:
        self._background(
            lambda: self.messages.put(("connected", self._discover())),
            "Controllo connessione ADB...",
        )

    def _run_adb(self, args: list[str], *, input_text: str | None = None) -> str:
        adb = self._adb()
        done = subprocess.run(
            [str(adb), *args], input=input_text, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=40, check=False,
        )
        output = (done.stdout + "\n" + done.stderr).strip()
        if done.returncode != 0:
            raise RuntimeError(output or "Comando ADB non riuscito")
        return output

    def find_wifi(self) -> None:
        def work() -> None:
            output = self._run_adb(["mdns", "services"])
            endpoints = re.findall(
                r"_adb-tls-connect\._tcp\s+(\d{1,3}(?:\.\d{1,3}){3}:\d{1,5})", output,
            )
            endpoints = sorted(set(ep for ep in endpoints if endpoint_is_valid(ep)))
            if len(endpoints) != 1:
                raise RuntimeError(
                    "Impossibile identificare un solo telefono Wi-Fi. "
                    "Verifica Debug wireless e la rete del PC; poi riprova."
                )
            self._run_adb(["connect", endpoints[0]])
            self.messages.put(("connected", self._discover()))

        self._background(work, "Cerco il telefono nella rete Wi-Fi...")

    def pair_wifi(self) -> None:
        endpoint = simpledialog.askstring(
            "Associa telefono",
            "Sul telefono: Debug wireless → Associa con codice.\n"
            "Inserisci qui IP e porta DI ASSOCIAZIONE (es. 192.168.1.50:37123):",
            parent=self,
        )
        if endpoint is None:
            return
        if not endpoint_is_valid(endpoint):
            messagebox.showerror("Indirizzo non valido", "Inserisci IP:porta visualizzati sul telefono.")
            return
        code = simpledialog.askstring("Codice di associazione", "Inserisci il codice di 6 cifre:", parent=self)
        if code is None:
            return
        if not re.fullmatch(r"\d{6}", code):
            messagebox.showerror("Codice non valido", "Il codice deve contenere 6 cifre.")
            return

        def work() -> None:
            # No shell and no password persistence: supply pairing code on stdin.
            output = self._run_adb(["pair", endpoint.strip()], input_text=code + "\n")
            self.messages.put(("notice", "Associazione riuscita. Premi 'Cerca tramite Wi-Fi'. "
                               + output.split("\n")[0]))

        self._background(work, "Associo il telefono al PC...")

    def _show_connection(self, adb: Path, connected: Any, info: Any, profile: Any) -> None:
        self.connection = (adb, connected, info, profile)
        self.results.clear()
        self.device_text.set(f"{info.model}  ·  Android {info.android}  ·  HyperOS {info.hyperos}")
        if profile["status"] == "verified-on-one-device":
            self.profile_text.set("Compatibilità verificata: " + profile["name"])
            self.notice.set("Telefono collegato. Ora puoi analizzare le impostazioni.")
        else:
            self.profile_text.set("Dispositivo non testato: solo rilevamento, nessuna modifica disponibile.")
            self.notice.set("Su questo dispositivo il toolkit non effettua modifiche.")
        self._render_rows(profile)

    def _render_rows(self, profile: dict[str, Any]) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.rows.clear()
        actions = [a for a in profile.get("actions", []) if a.get("analyzable", True)
                   and a.get("maturity") != "experimental"]
        if not actions:
            self._label(self.list_frame, "Nessuna modifica verificata per questo telefono.",
                        color=YELLOW).pack(anchor="w", pady=20)
            return
        for action in actions:
            aid = action["id"]
            title, desc = LABELS.get(aid, (action["title"], "Controllo di compatibilità."))
            card = tk.Frame(self.list_frame, bg=PANEL, padx=17, pady=12, highlightbackground=BORDER,
                            highlightthickness=1)
            card.pack(fill="x", pady=(0, 10))
            self._label(card, title, bold=True, size=12).pack(anchor="w")
            self._label(card, desc, color=MUTED, size=9, wraplength=710, justify="left").pack(
                anchor="w", pady=(3, 3),
            )
            state = self._label(card, "Da controllare", color=YELLOW, size=9)
            state.pack(anchor="w", pady=(1, 7))
            buttons = tk.Frame(card, bg=PANEL)
            buttons.pack(anchor="w")
            analyze = self._button(buttons, "Controlla", lambda a=aid: self.inspect_action(a), "#234b79")
            analyze.pack(side="left", padx=(0, 8))
            apply = self._button(buttons, "Disattiva", lambda a=aid: self.apply_action(a))
            apply.pack(side="left", padx=(0, 8))
            apply.configure(state="disabled")
            restore = self._button(buttons, "Ripristina da log", lambda a=aid: self.restore_action(a),
                                   "#304660")
            restore.pack(side="left")
            can_restore = action.get("restore_mode") == "automatic"
            restore.configure(state="normal" if can_restore else "disabled")
            self.rows[aid] = {
                "action": action, "status": state,
                "analyze_button": analyze, "apply_button": apply, "restore_button": restore,
                "enabled": {"analyze_button": "normal", "apply_button": "disabled",
                            "restore_button": "normal" if can_restore else "disabled"},
            }

    def _executor(self, operation: str) -> tuple[ActionExecutor, RunLog]:
        if self.connection is None:
            raise RuntimeError("Collega un telefono prima di continuare.")
        _adb, connected, info, profile = self.connection
        log = RunLog(Path("runtime/logs").resolve(), operation, connected.serial, info, profile["id"])
        return ActionExecutor(connected.serial, profile, log), log

    def _job(self, mode: str, action_id: str | None = None, log_path: Path | None = None,
             ack: bool = False) -> None:
        def work() -> None:
            executor, run_log = self._executor(mode)
            try:
                if mode == "analyze":
                    ids = [action_id] if action_id else [
                        a["id"] for a in executor.profile["actions"]
                        if a.get("analyzable", True) and a.get("maturity") != "experimental"
                    ]
                    for aid in ids:
                        result = executor.analyze(aid)
                        self.messages.put(("result", result))
                elif mode == "apply" and action_id:
                    result = executor.apply(action_id, action_id, ack)
                    self.messages.put(("result", result))
                elif mode == "restore" and action_id and log_path:
                    result = executor.restore(log_path, action_id, action_id)
                    self.messages.put(("result", result))
                self.messages.put(("notice", "Operazione conclusa. Registro locale: " + str(run_log.path)))
            finally:
                try:
                    executor.press_home()
                except Exception:
                    pass

        self._background(work, "Operazione in corso. Lascia il telefono sbloccato...")

    def analyze_all(self) -> None:
        if self.connection is None:
            messagebox.showinfo("Telefono non collegato", "Premi prima 'Trova telefono'.")
            return
        self._job("analyze")

    def inspect_action(self, aid: str) -> None:
        self._job("analyze", aid)

    def apply_action(self, aid: str) -> None:
        row = self.rows[aid]
        if row["enabled"]["apply_button"] == "disabled":
            messagebox.showinfo("Prima analizza", "Controlla l'impostazione prima di modificarla.")
            return
        title = LABELS.get(aid, (aid, ""))[0]
        if not messagebox.askyesno(
            "Conferma modifica",
            f"Vuoi disattivare '{title}' sul telefono?\n\n"
            "L'operazione riguarda soltanto questa impostazione.",
        ):
            return
        ack = False
        if row["action"].get("risk") == "server-data-deletion":
            ack = messagebox.askyesno(
                "Avviso Xiaomi: dati associati",
                "Xiaomi avverte che revocare MSA può eliminare i relativi dati "
                "già raccolti sui suoi server e rendere inutilizzabile il servizio.\n\n"
                "La riattivazione MSA è attualmente MANUALE.\n\n"
                "Hai compreso l'avviso e vuoi procedere?",
            )
            if not ack:
                return
        self._job("apply", aid, ack=ack)

    def restore_action(self, aid: str) -> None:
        if self.connection is None:
            return
        action = self.rows[aid]["action"]
        if action.get("restore_mode") != "automatic":
            messagebox.showinfo("Ripristino manuale", action.get("manual_restore", "Non disponibile."))
            return
        path = filedialog.askopenfilename(
            title="Seleziona il log della modifica effettuata su questo telefono",
            initialdir=str(Path("runtime/logs").resolve()), filetypes=[("Registro JSON", "*.json")],
        )
        if not path:
            return
        try:
            source = json.loads(Path(path).read_text(encoding="utf-8"))
            _adb, connected, info, profile = self.connection
            if source.get("profile") != profile["id"] or source.get("device_reference") != opaque_device_reference(connected.serial):
                raise ValueError(
                    "Il log non corrisponde alla connessione e al profilo attuali. "
                    "Se usi Wi-Fi e la porta è cambiata, ricollegati tramite lo stesso endpoint; "
                    "non ripristinare un log di origine incerta."
                )
            if not any(r.get("action_id") == aid and r.get("status") == "changed"
                       and r.get("initial") is True and r.get("final") is False
                       for r in source.get("results", [])):
                raise ValueError("Il log non contiene una modifica ripristinabile per questa funzione.")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror("Registro non valido", str(exc))
            return
        if messagebox.askyesno("Conferma ripristino", "Ripristinare l'impostazione precedente?"):
            self._job("restore", aid, log_path=Path(path))

    def _show_result(self, result: Any) -> None:
        row = self.rows.get(result.action_id)
        if row is None:
            return
        statuses = {
            "changed": ("Modifica applicata e verificata", GREEN),
            "already-disabled": ("Già disattivata", GREEN),
            "analyzed": (
                "Attiva: puoi disattivarla" if result.initial is True else "Già disattivata",
                YELLOW if result.initial is True else GREEN,
            ),
            "restored": ("Ripristinata", GREEN),
            "unsupported-or-failed": ("Non verificabile su questa schermata", RED),
            "failed": ("Modifica non riuscita", RED),
            "restore-failed": ("Ripristino non riuscito", RED),
        }
        label, color = statuses.get(result.status, (result.status, YELLOW))
        row["status"].configure(text=label, fg=color)
        row["enabled"]["apply_button"] = (
            "normal" if result.status == "analyzed" and result.initial is True
            and row["action"].get("writable") else "disabled"
        )
        if not self.busy:
            row["apply_button"].configure(state=row["enabled"]["apply_button"])
        self.results[result.action_id] = result


def main() -> None:
    app = PrivacyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
