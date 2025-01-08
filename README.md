# YouTube Video Uploader

Ein Python-Skript zur Automatisierung des Videouploads auf YouTube mit erweiterten Funktionen wie Playlist-Zuweisung und Geolocation.

## Inhaltsverzeichnis
- [Beschreibung](#beschreibung)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Verwendung](#verwendung)
- [Hinweise](#hinweise)
- [Lizenz](#lizenz)

## Beschreibung
Dieses Script erlaubt Ihnen das Hochladen von Videos auf YouTube, wobei zusätzliche Daten wie Playlist-Zuweisung und geographische Koordinaten hinzugefügt werden können.

## Voraussetzungen
- **Python 3.x**
- `google-api-python-client`
- `oauth2client`

## Installation
1. Installieren Sie die benötigten Bibliotheken:
   ```sh
   pip install google-api-python-client oauth2client

2. Erhalten Sie OAuth 2.0 Anmeldeinformationen:
   - Erstellen Sie ein Projekt in der Google API Console.
   - Aktivieren Sie die YouTube Data API v3 für Ihr Projekt.
   - Erstellen Sie eine OAuth 2.0 Client-ID und speichern Sie die client_secrets.json Datei in Ihrem Projektverzeichnis.