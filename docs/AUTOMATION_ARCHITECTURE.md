# Architektur des autonomen Master-Loops

`run_loop.sh` ist der reproduzierbare Einstiegspunkt für Anwendungsprüfung,
Demoausführung und Videoproduktion. Der Shell-Wrapper verwendet
`set -euo pipefail`, registriert einen Cleanup-Trap und startet ausschließlich
den typisierten Python-Controller `automation.run_loop`.

## Zustandsmaschine

Die feste Reihenfolge lautet:

```text
DISCOVER → PRECHECK → PLAN → IMPLEMENT → STATIC_CHECK → UNIT_TEST
→ INTEGRATION_TEST → SECURITY_CHECK → APPLICATION_QA → DEMO_PRECHECK
→ DEMO_RUN → RECORD → GENERATE_NARRATION → GENERATE_VOICE
→ GENERATE_SUBTITLES → RENDER → VIDEO_QA → FINAL_VERIFY → COMPLETE
```

Kommandos stammen aus einer statischen Registry in `automation/gates.py`; weder
Statusdateien noch Timeline können beliebige Shellbefehle einschleusen. Jede
Phase besitzt ein festes Timeout. Fehler werden klassifiziert, sensible Token in
Ausgaben geschwärzt und maximal dreimal je Phase wiederholt. Zusätzlich beendet
ein globales Iterationslimit den Lauf sicher.

Der Zustand liegt in `automation/state/loop_state.json` und wird mit temporärer
Datei, `fsync` und atomarem Rename geschrieben. Er enthält abgeschlossene,
fehlgeschlagene und blockierte Phasen, Retry-Zähler, letzte Diagnose und den
Fortsetzungspunkt. Das Lock-Verzeichnis `.automation-loop.lock` verhindert zwei
gleichzeitige Master-Loops; das strukturierte JSONL-Log wird größenbegrenzt
rotiert.

## Externe Voraussetzungen

Ein fehlender TTS-Schlüssel ist kein behaupteter Erfolg und kein Grund, andere
Arbeit abzubrechen. Die Phase wird als `BLOCKED_EXTERNAL_CREDENTIAL` gespeichert,
der Loop erzeugt Untertitel, stumme Vorschau und technische Video-QA weiter und
endet mit Exitcode 42 sowie Status `READY_EXCEPT_EXTERNAL_BLOCKER`.

Nach sicherer Bereitstellung des Schlüssels genügt:

```bash
export OPENAI_API_KEY='...'
./run_loop.sh --resume
```

Die Zustandsmaschine beginnt dann an `GENERATE_VOICE`. Nach erfolgreicher Phase
werden Blocker und Resume-Marke entfernt; Render, Video-QA und Finalprüfung laufen
erneut. Der Schlüssel wird nicht persistiert und Logausgaben werden defensiv
redigiert.

## Bedienung

```bash
./run_loop.sh --dry-run  # Werkzeuge, Timeline und geplante Phasen prüfen
./run_loop.sh            # neuen begrenzten Lauf starten
./run_loop.sh --resume   # vorhandenen Zustand sicher fortsetzen
```

Der Dry-Run erzeugt weder Video noch Produktdaten. Laufzeitdetails stehen in
`automation/logs/master-loop.jsonl`; der lesbare Abschlussbericht wird nach
`dist/build_report.md` geschrieben.
