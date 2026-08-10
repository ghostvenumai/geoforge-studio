# Reproduzierbare GeoForge-Produktdemo

Die Video-Pipeline erzeugt aus demselben validierten Szenenplan eine echte
Browseraufnahme, Sprechertexte, Untertitel und ein technisch geprüftes
1920×1080-MP4. Sie verwendet feste UI-Selektoren und lokale Dienste statt
zufälliger Mauskoordinaten oder manueller Desktop-Automation.

## Schnellprüfung

```bash
make video-dry-run
```

Die Prüfung verändert keine Produktdaten und kontrolliert FFmpeg, FFprobe,
Chrome, Playwright, die projektlokale Node-Laufzeit, Python,
Marketing-Demodaten und die 147-Sekunden-Timeline.
Ein fehlender `OPENAI_API_KEY` wird separat als externer, optionaler Blocker
gemeldet. Die Anwendung selbst benötigt diesen Schlüssel nicht.

## Vollständiger Ablauf

```bash
# Technisch vollständige, aber stumme Vorschau mit eingebrannten Untertiteln
make video-preview

# Finale Version mit deutscher OpenAI-Sprachausgabe
export OPENAI_API_KEY='...'
make video
```

`make video` verwendet standardmäßig `gpt-4o-mini-tts`, die Stimme `coral` und
WAV-Segmente. Modell und Stimme lassen sich mit `OPENAI_TTS_MODEL` und
`OPENAI_TTS_VOICE` konfigurieren. Der Schlüssel wird weder in Dateien noch in
Logs geschrieben. Ohne Schlüssel wird keine TTS-Netzwerkanfrage ausgeführt.

Die TTS-Ausgabe wird pro Szene anhand eines SHA-256-Hashes gecacht. Ein erneuter
Lauf mit `--resume` verwendet gültige Aufnahme- und Audioartefakte weiter. Die
Audiosegmente werden auf die geplante Szenendauer aufgefüllt oder begrenzt.

## Artefakte

| Datei | Bedeutung |
|---|---|
| `video/script/timeline.json` | einzige Quelle für Reihenfolge, Dauer, Text und Overlay |
| `video/script/narration.md` | automatisch erzeugter deutscher Sprechertext |
| `video/tmp/capture.webm` | echte Playwright-Browseraufnahme |
| `video/tmp/subtitles.srt` | zeitlich aus derselben Timeline erzeugte Untertitel |
| `video/tmp/audio/` | gecachte, nicht versionierte Szenen-Audiodateien |
| `dist/solcom_demo_preview.mp4` | stumme Vorschau bei fehlendem TTS-Schlüssel |
| `dist/solcom_demo.mp4` | finales Video mit Sprachausgabe |
| `dist/video_qa.json` | FFprobe-/Audio-Prüfergebnis |
| `dist/build_report.md` | Phasenstatus und dokumentierter Blocker |

Große und generierte Audio-/Videoartefakte sind bewusst von Git ausgeschlossen.
Die Timeline, Automatisierung, Tests und Dokumentation bleiben versioniert und
machen den Build reproduzierbar.

## Fehlerbehebung

- Exitcode `30`: erforderliches Werkzeug oder Timeline ungültig.
- Exitcode `40`: Browseraufnahme fehlgeschlagen; siehe `video/logs/recording.log`.
- Exitcode `42`: ausschließlich externe TTS-Voraussetzung fehlt; Vorschau und
  alle lokalen Prüfungen können trotzdem vollständig vorliegen.
- Exitcode `50`: FFmpeg-Renderfehler.
- Exitcode `60`: MP4 erfüllt die technischen Video-QA-Kriterien nicht.

Gezielt fortsetzen:

```bash
./video/build_demo.sh record --resume
./video/build_demo.sh narration
./video/build_demo.sh subtitles
./video/build_demo.sh render
./video/build_demo.sh qa
```
