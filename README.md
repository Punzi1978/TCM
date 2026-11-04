# 📄 PDF Tabellenscraper & Informations-Extraktor

Eine Web-Anwendung zum automatischen Extrahieren von Informationen aus PDF-Tabellen und verlinkten Websites.

## ✨ Features

- PDF-Tabelle von URL herunterladen und parsen
- Nach beliebigen Spalten sortieren
- Informationen von Webseiten extrahieren (Name, E-Mail, Telefon, Adresse, etc.)
- Ergebnisse als CSV exportieren

## 🚀 Live-Version

Klicke hier: **[Live Demo](https://deine-streamlit-url.streamlit.app)**

Keine Installation nötig! Einfach den Link öffnen.

## 🏗️ Lokale Installation (optional)

Falls du die App selbst hosten möchtest:

### Voraussetzungen

- Python 3.9 oder höher
- pip

### Installation

```bash
# Virtuelle Umgebung erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -r requirements.txt

# App starten
streamlit run app.py
```

## 📦 Deployment

### Auf Streamlit Cloud (empfohlen)

1. Code auf GitHub pushen
2. Auf [Streamlit Cloud](https://streamlit.io/cloud) anmelden
3. "New App" → Repository auswählen
4. Deploy klicken

### Als Single Executable (für lokale Verteilung)

Siehe `build_executable.sh` für PyInstaller-Vorgehensweise.

## 🔧 Konfiguration

In `app.py` können folgende Dinge angepasst werden:
- Maximal Anzahl zu verarbeitender Zeilen
- Zu extrahierende Informationstypen
- Timeouts und Delay zwischen Anfragen

## ⚠️ Rechtlicher Hinweis

Bitte stelle sicher, dass du:
- Die robots.txt der Zielseiten respektierst
- Die Nutzungsbedingungen nicht verstößt
- Nicht zu viele Anfragen in kurzer Zeit sendest (Delay ist standardmäßig eingestellt)

## 📝 License

MIT License - frei verwendbar
