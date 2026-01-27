# FTP Deployment & Management Werkzeuge

In diesem Verzeichnis befinden sich spezialisierte Python-Skripte, um die Plattform (Webinhalte) automatisiert auf einen Webserver zu übertragen und die dortige Struktur zu verwalten.

## Übersicht der Komponenten

### 1. ftp.json (Konfiguration)
Dies ist das Herzstück der Kommunikation. Die Datei enthält alle notwendigen Zugangsdaten und Pfadangaben. 
**Wichtig:** Aus Sicherheitsgründen ist diese Datei nicht im öffentlichen Repository enthalten und befindet sich in der .gitignore. Sie muss lokal manuell erstellt werden.

**Struktur der ftp.json:**
```json
{
  "ftp": {
    "host": "ihr.ftp.server.com",
    "user": "benutzername",
    "pass": "passwort",
    "port": 21
  },
  "paths": {
    "local_root_dir": "Website",
    "remote_root_dir": "/httpdocs/odata-guide"
  }
}
```

### 2. 	[testftp.py](testftp.py) (Diagnose Werkzeug)
Dieses Skript dient zur Überprüfung der Verbindung und zur Bestandsaufnahme auf dem Server.
- **Funktionsweise:** Es lädt die Konfiguration aus der ftp.json, stellt eine gesicherte Verbindung her und versucht, sich anzumelden.
- **Leistung:** Nach erfolgreicher Anmeldung wird der gesamte Verzeichnisbaum des Zielservers rekursiv ausgelesen.
- **Ergebnis:** Die Struktur wird direkt in der Konsole ausgegeben und zusätzlich als detaillierte Liste in einer Datei namens listing.csv gespeichert. Dies hilft, den aktuellen Stand des Webservers vor einem Upload zu verifizieren.

### 3. [uploadftp.py](./uploadftp.py) (Synchronisierung)
Dieses Skript übernimmt den eigentlichen Datentransfer vom lokalen Rechner zum Webserver.
- **Funktionsweise:** Es liest das in der Konfiguration definierte Quellverzeichnis (z. B. der Website-Ordner) und spiegelt diesen Inhalt auf den Server.
- **Automatisierung:** Das Skript arbeitet rekursiv. Das bedeutet, es erkennt Unterverzeichnisse, erstellt diese auf dem Server, falls sie noch nicht existieren, und überträgt alle Dateien (Bilder, Skripte, HTML-Seiten) einzeln.
- **Sicherheit:** Nach Abschluss des Vorgangs wird die Verbindung ordnungsgemäß getrennt und eine Erfolgsmeldung ausgegeben.

## Nutzungshinweise
1. Stellen Sie sicher, dass Python installiert ist.
2. Erstellen Sie eine tp.json im Ordner tp/ basierend auf dem oben gezeigten Muster.
3. Führen Sie 	estftp.py aus, um die Erreichbarkeit des Servers zu prüfen.
4. Nutzen Sie uploadftp.py, um die neuesten Änderungen der Webseite live zu schalten.
