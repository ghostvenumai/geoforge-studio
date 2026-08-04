# GeoForge Studio – Bedienungsanleitung

Diese Anleitung beschreibt den vollständigen Arbeitsablauf vom Start der Anwendung bis zum geprüften Export. Die Weboberfläche ist deutschsprachig. Technische Feldnamen, API-Pfade und YAML-Schritttypen bleiben aus Kompatibilitätsgründen englisch.

## 1. Anwendung vorbereiten und starten

Vorausgesetzt werden Python 3.12, npm und ein lokaler Chrome-Browser. Beim ersten Start werden die Abhängigkeiten einmalig in den Projektordner installiert:

```bash
cd /home/serverserver/geoforge-studio
./scripts/bootstrap.sh
```

Anschließend starten Sie Backend und Frontend gemeinsam:

```bash
./scripts/start_demo.sh
```

Falls Port 8000 bereits belegt ist, wählen Sie beispielsweise einen freien Backend-Port:

```bash
GEOFORGE_BACKEND_PORT=18080 ./scripts/start_demo.sh
```

Die Oberfläche bleibt unter Port 5173 erreichbar und verbindet sich automatisch mit dem gewählten Backend-Port.

Sobald „GeoForge Studio ist bereit“ erscheint, öffnen Sie:

- Weboberfläche: http://127.0.0.1:5173
- API-Zustand: http://127.0.0.1:8000/api/health
- interaktive API-Dokumentation: http://127.0.0.1:8000/docs

Bei einem abweichenden Backend-Port ersetzen Sie in den beiden API-Adressen 8000 durch den gewählten Wert.

Beenden Sie beide Dienste mit:

```bash
./scripts/stop_demo.sh
```

Falls noch keine Beispieldatei vorhanden ist:

```bash
.venv/bin/python scripts/generate_demo_data.py \
  --rows 1000 \
  --seed 42 \
  --output data/samples/geoforge-demo.csv \
  --format csv \
  --error-rate 0.12 \
  --duplicate-rate 0.08
```

Die Datei enthält ausschließlich synthetische Daten und absichtlich eingebaute Qualitätsprobleme.

## 2. Empfohlener vollständiger Arbeitsablauf

### Schritt 1: Datensatz importieren

1. Öffnen Sie links **Datensätze**.
2. Ziehen Sie `data/samples/geoforge-demo.csv` auf die Uploadfläche oder klicken Sie darauf und wählen Sie die Datei aus.
3. Warten Sie, bis die Meldung „geoforge-demo hochgeladen“ erscheint.
4. Kontrollieren Sie in der Tabelle Dateiname, Format, Zeilen, Spalten, Größe, Status und Importzeitpunkt.

Unterstützt werden CSV, JSON, JSONL/NDJSON, Parquet und XLSX. Das Backend prüft Erweiterung und Größe, bereinigt den Dateinamen, verhindert Pfadmanipulationen und speichert das Original unverändert. Eine SHA-256-Prüfsumme erkennt, ob dieselbe Datei bereits importiert wurde.

Zum Löschen wählen Sie das Papierkorb-Symbol. Erst nach Bestätigung werden Metadaten, Originaldatei und abgeleitete Profildaten entfernt. Datensätze, die bereits von einem Lauf referenziert werden, können nicht gelöscht werden; das Backend antwortet in diesem Fall mit Status 409. So bleiben Lauf- und Audit-Nachweise konsistent.

### Schritt 2: Datenprofil erstellen

1. Öffnen Sie **Datenprofiling**.
2. Wählen Sie oben den importierten Datensatz.
3. Klicken Sie auf **Profiling starten**.
4. Prüfen Sie die Kennzahlen Qualitätswert, Zeilen, Nullwerte, ungültige Werte und exakte Dubletten.
5. Lesen Sie in der Spaltentabelle Datentyp, Nullwertquote, Eindeutigkeitsquote, Beispielwerte, Fehleranzahl und empfohlene Transformation.

Bei größeren Dateien arbeitet das Profiling mit einer begrenzten Stichprobe. Die Oberfläche kennzeichnet dann die Anzahl der untersuchten Zeilen. Der Qualitätswert ist ein Indikator; er ersetzt nicht die Prüfung der einzelnen Warnungen.

### Schritt 3: Pipeline auswählen und prüfen

1. Öffnen Sie **Pipeline-Builder**.
2. Wählen Sie als Pipeline **Vollständige Datenqualität und Deduplizierung**.
3. Wählen Sie als Eingabedatensatz die zuvor importierte Datei.
4. Klicken Sie auf einen Knoten. Rechts erscheinen Name, technischer Schritttyp und validierte JSON-Konfiguration.
5. Klicken Sie auf **Validieren**. Eine grüne Meldung mit der Pipeline-Prüfsumme bestätigt eine gültige Konfiguration.

Die drei mitgelieferten Pipelines sind:

- **Bereinigung deutscher Adressen**: Unicode, Leerzeichen, Straße, Ort, Postleitzahl und Original-/Normalisiert-Felder.
- **Koordinatenprüfung und -transformation**: Wertebereiche, vertauschte Koordinaten und CRS-Transformation.
- **Vollständige Datenqualität und Deduplizierung**: Adressbereinigung, Validierung, Quarantäne und blockierte Fuzzy-Dublettenprüfung.

### Schritt 4: Pipeline visuell bearbeiten

In der **Schrittauswahl** links stehen alle erlaubten Operatoren. Sie können einen Schritt anklicken oder auf die Arbeitsfläche ziehen. Verbinden Sie die Anschlussstellen der Knoten, um die Ausführungsreihenfolge festzulegen.

- **Rückgängig/Wiederholen** verändert den lokalen Bearbeitungsstand.
- **Validieren** sendet die Definition an das Backend, ohne sie auszuführen.
- **Als Version speichern** erzeugt eine neue unveränderliche Pipeline-Version.
- **YAML-Ansicht** wechselt zum Texteditor.
- **YAML importieren/exportieren** tauscht sichere Pipeline-Definitionen aus.

Eine Konfiguration im rechten Bereich muss gültiges JSON sein. YAML und JSON dürfen nur die dokumentierten Schrittmodelle enthalten. Python-, Shell- oder andere ausführbare Inhalte werden nicht ausgeführt.

Wichtig: Der technische YAML-Wert eines Schritts bleibt beispielsweise `normalize_address`; die Oberfläche zeigt dafür „Adresse normalisieren“. Dadurch bleiben exportierte Pipelines sprach- und versionsstabil.

### Schritt 5: Pipeline ausführen

1. Prüfen Sie erneut Pipeline und Eingabedatensatz.
2. Klicken Sie oben rechts auf **Pipeline ausführen**.
3. Die Meldung „Lauf … wurde eingereiht“ enthält die verkürzte Lauf-ID.
4. Wechseln Sie zu **Läufe und Audit**.
5. Beobachten Sie den Status: Eingereiht → Läuft → Abgeschlossen.

Ein laufender oder eingereihter Auftrag kann über **Abbrechen** gestoppt werden. Der Run Manager erfasst pro Schritt Laufzeit, Eingabe-/Ausgabezeilen, veränderte Zeilen, Quarantänezeilen, Warnungen und Fehler.

### Schritt 6: Ergebnis fachlich prüfen

Nutzen Sie anschließend diese Ansichten:

- **Adressverarbeitung** zeigt die Ergebnisvorschau mit Original- und normalisierten Feldern wie `street_original` und `street_normalized`.
- **Geoverarbeitung** zeigt gültige, vertauschte und quarantänisierte Koordinaten sowie eine lokale Punktkarte. Es werden keine Daten an einen Kartendienst übertragen.
- **Qualitätsanalyse** vergleicht den Qualitätswert vor und nach dem Lauf. Quarantäne und unerklärter Zeilenverlust werden getrennt dargestellt, damit Löschen nicht als künstliche Qualitätsverbesserung erscheint.
- **Performance** zeigt tatsächlich gemessene Laufzeit, Durchsatz, CPU, Spitzenspeicher und Schrittdauern. Darunter werden die gemessenen CSV-/Parquet-Benchmarks dargestellt.

### Schritt 7: Dubletten entscheiden

1. Öffnen Sie **Dublettenprüfung**.
2. Wählen Sie einen Lauf mit gefundenen Kandidaten.
3. Wählen Sie links eine Gruppe, besonders einen Treffer mit Review-Bedarf.
4. Vergleichen Sie die Datensätze spaltenweise. Abweichende Werte sind farblich hervorgehoben.
5. Bestimmen Sie im Auswahlfeld den **kanonischen Datensatz**.
6. Klicken Sie auf **Annehmen** oder **Ablehnen**.

Die Entscheidung wird gespeichert. Die Erkennung vergleicht nicht jede Zeile unbeschränkt mit jeder anderen, sondern erzeugt Kandidaten über Blocking-Spalten und begrenzte Gruppengrößen.

### Schritt 8: Artefakte exportieren

1. Öffnen Sie **Exporte**.
2. Wählen Sie einen abgeschlossenen Lauf.
3. Laden Sie das gewünschte Artefakt über **Herunterladen**.

Ein vollständiger Lauf erzeugt:

- Ergebnis als CSV, JSONL und Parquet
- Quarantänedatensatz
- Qualitätsbericht
- Leistungsbericht
- Pipeline-YAML
- Audit-Protokoll
- Laufmanifest
- SHA-256-Prüfsummen

CSV-Ausgaben schützen Textwerte vor Spreadsheet-Formel-Injection. Das Laufmanifest enthält unter anderem Softwareversion, Eingabe- und Pipeline-Prüfsumme, Zeilenzahlen, Warnungen, Fehler, Schrittlaufzeiten und Artefakte.

## 3. Bedeutung der Navigation

- **Übersicht**: Gesamtkennzahlen und Trends aus realen Backend-Daten.
- **Datensätze**: Import, Dateiprüfung, Vorschau und Löschen.
- **Datenprofiling**: Statistische Analyse und Transformationsvorschläge.
- **Pipeline-Builder**: Visuelle/YAML-basierte Pipeline-Erstellung und Ausführung.
- **Adressverarbeitung**: Vorher-Nachher-Prüfung normalisierter Adressen.
- **Geoverarbeitung**: Koordinatenprüfung, Transformation und lokale Karte.
- **Dublettenprüfung**: Manuelle Entscheidung unsicherer Treffer.
- **Qualitätsanalyse**: Qualitäts-, Quarantäne- und Verlustvergleich.
- **Performance**: Reale Lauf- und Benchmark-Metriken.
- **Läufe und Audit**: Persistente Ausführungshistorie und Abbruch.
- **Exporte**: Ergebnis- und Nachweisdateien.
- **Systemstatus**: API, Datenbank, Speicher, Speicherverbrauch und Versionen.
- **Architektur**: Überblick über Frontend, API, Engine, Fachlogik und Nachweise.

## 4. Bedienung, Darstellung und Datenschutz

Mit dem Mond-/Sonnensymbol rechts oben wechseln Sie zwischen hellem und dunklem Modus. Auf Tablet und Mobilgerät öffnen Sie die Navigation über das Menüsymbol. Alle Hauptfunktionen sind per Tastatur erreichbar; sichtbare Fokusrahmen zeigen die aktuelle Position.

GeoForge Studio arbeitet im Standardbetrieb lokal. Es benötigt keine API-Schlüssel, keinen Geocoder, keinen Analyse-Endpunkt und keinen externen Kartendienst. Verwenden Sie für die Demo ausschließlich synthetische oder ausdrücklich freigegebene Daten.

## 5. Typische Fehler und Lösungen

### Die Anwendung startet nicht

Prüfen Sie:

```bash
curl http://127.0.0.1:8000/api/health
tail -n 100 artifacts/runtime/backend.log
tail -n 100 artifacts/runtime/frontend.log
```

Stoppen Sie alte Prozesse mit `./scripts/stop_demo.sh` und starten Sie anschließend neu.

### Upload wird abgelehnt

Prüfen Sie Dateiendung, Dateigröße und ob die Datei tatsächlich zum angegebenen Format passt. Verwenden Sie bei CSV UTF-8, sofern möglich. Eine identische Prüfsumme wird als Dateidublette gemeldet.

### Profiling zeigt noch keine Daten

Wählen Sie einen Datensatz und klicken Sie explizit auf **Profiling starten**. Nach einem Datensatzwechsel wird das zugehörige Profil neu geladen.

### Pipeline lässt sich nicht validieren

Wechseln Sie zur YAML-Ansicht oder prüfen Sie rechts die JSON-Konfiguration. Jeder Schritt benötigt eine eindeutige ID, einen erlaubten Typ und die für diesen Typ vorgeschriebenen Felder. Es dürfen keine Zyklen oder Verbindungen zu unbekannten Knoten enthalten sein.

### Keine Dublettengruppe sichtbar

Verwenden Sie einen abgeschlossenen Lauf der Pipeline „Vollständige Datenqualität und Deduplizierung“. Eine Gruppe erscheint nur, wenn der konfigurierte Mindestscore erreicht wurde.

### Export ist leer oder nicht verfügbar

Artefakte werden erst nach einem erfolgreich abgeschlossenen Lauf erzeugt. Prüfen Sie den Status unter **Läufe und Audit**.

## 6. Schneller Demonstrationsablauf

Für eine Präsentation in fünf Minuten:

1. Demodatei importieren.
2. Profiling starten und Qualitätsprobleme zeigen.
3. vollständige Pipeline im Builder validieren und ausführen.
4. Qualitätsvergleich und Dublettengruppe prüfen.
5. Performance-Metriken öffnen.
6. Parquet-Ergebnis und Laufmanifest herunterladen.
7. Seite neu laden und den persistenten Lauf erneut zeigen.

Weitere technische Details stehen in `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `TESTING.md` und `FINAL_REPORT.md`.
