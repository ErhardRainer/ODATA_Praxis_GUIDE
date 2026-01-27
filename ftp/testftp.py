import json
from ftplib import FTP
import socket
from ftplib import error_perm
import posixpath
import csv
import os

# --- Funktion zum Laden der Konfiguration ---

def load_config(filename='ftp.json'):
    """Lädt die Konfiguration aus einer JSON-Datei im selben Verzeichnis wie diesem Skript."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, filename)
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"FEHLER: Die Konfigurationsdatei '{config_path}' wurde nicht gefunden.")
        exit(1)
    except json.JSONDecodeError:
        print(f"FEHLER: Die Datei '{config_path}' enthält ungültiges JSON.")
        exit(1)

# --- Testfunktion ---

def test_ftp_connection(host, user, password, port):
    """
    Versucht, eine Verbindung zum FTP-Server herzustellen und sich anzumelden.
    """
    print(f"Starte Verbindungstest zu {host}:{port} mit Benutzer '{user}'...")
    
    try:
        with FTP(timeout=10) as ftp:
            ftp.connect(host, port)
            print("Status: Verbindung zum Server erfolgreich hergestellt.")
            
            ftp.login(user=user, passwd=password)
            print("Status: ✅ Erfolgreich angemeldet.")
            
            # Zeige kurze Begrüßung
            try:
                welcome = ftp.getwelcome()
                print(f"Server-Begrüßung: {welcome}")
            except Exception:
                pass

            # Starte rekursives Listing ab dem aktuellen Verzeichnis
            start_dir = '.'
            current = ftp.pwd() if hasattr(ftp, 'pwd') else start_dir
            print(f"Startverzeichnis: {current}")
            print('\nAuflisten aller Verzeichnisse und Dateien:')
            entries = list_all(ftp, start_dir)

            # Optional: CSV export
            try:
                with open('listing.csv', 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile, delimiter='|')
                    writer.writerow(['Folder', 'File', 'Size'])
                    for folder, fname, size in entries:
                        writer.writerow([folder, fname, size])
                print(f"\nCSV exportiert nach: listing.csv")
            except Exception as e:
                print(f"Fehler beim Schreiben der CSV-Datei: {e}")

            ftp.quit()
            print("\n*** Verbindungstest + Auflistung: ERFOLGREICH! ***")

    except socket.gaierror:
        print("\n*** Fehler: KONNTE HOST NICHT AUFLÖSEN ***")
    except socket.timeout:
        print(f"\n*** Fehler: TIMEOUT ***")
    except Exception as e:
        print(f"\n*** Fehler: ANMELDUNG ODER ALLGEMEINE FEHLER ***")
        if '530 Login incorrect' in str(e):
            print("-> Überprüfe deinen Benutzernamen und dein Passwort.")
        else:
            print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

def list_all(ftp, path='.', indent=0):
    """Rekursives Auflisten eines FTP-Pfads.

    Versucht zuerst `mlsd` (liefert Typen), fällt auf `nlst` + `cwd`-Probe zurück,
    wenn MLSD nicht unterstützt wird. Druckt eine einfache Baumstruktur.
    """
    prefix = '  ' * indent
    # Normalisiere Pfad für MLSD/NLST
    mlsd_path = path
    results = []
    try:
        # Versuche MLSD (moderne FTP-Server)
        try:
            entries = list(ftp.mlsd(mlsd_path))
        except (AttributeError, error_perm, Exception):
            entries = None

        if entries is not None:
            for name, facts in entries:
                typ = facts.get('type', '')
                if typ == 'dir':
                    print(f"{prefix}{name}/")
                    sub = posixpath.join(path, name) if path not in ('.', '/') else name
                    # Verzeichnis: rekursiv sammeln
                    child_results = list_all(ftp, sub, indent + 1)
                    if not child_results:
                        # Leeres Verzeichnis: als Eintrag (Folder | File/ | Size)
                        results.append((path, name + '/', ''))
                    else:
                        results.extend(child_results)
                else:
                    print(f"{prefix}{name}")
                    # Dateigröße aus facts (falls vorhanden)
                    size = facts.get('size') or ''
                    results.append((path, name, size))
            return results

        # Fallback: nlst + cwd-Probe
        try:
            names = ftp.nlst(path)
        except Exception as e:
            print(f"{prefix}Fehler beim Lesen von {path}: {e}")
            return results

        for entry in names:
            # nlst kann relative oder absolute Namen liefern; extrahiere Anzeige-Name
            display = entry.rstrip('/').split('/')[-1]
            if display in ('.', '..'):
                continue

            # Baue einen vollen Pfad, falls nötig
            if entry.startswith('/'):
                full = entry
            else:
                full = posixpath.join(path, display) if path not in ('.', '/') else display

            # Prüfe, ob es ein Verzeichnis ist, indem wir versuchen, hineinzuwechseln
            try:
                ftp.cwd(full)
                print(f"{prefix}{display}/")
                child_results = list_all(ftp, full, indent + 1)
                if not child_results:
                    results.append((path, display + '/', ''))
                else:
                    results.extend(child_results)
                # Zurück ins parent (einfach '..' verwenden)
                try:
                    ftp.cwd('..')
                except Exception:
                    pass
            except Exception:
                # Kein Verzeichnis oder kein Zugriff -> Datei
                print(f"{prefix}{display}")
                # versuche Größe zu ermitteln (kann fehlschlagen)
                size = ''
                try:
                    size = ftp.size(full)
                except Exception:
                    size = ''
                results.append((path, display, size))
    except Exception as e:
        print(f"{prefix}Fehler beim Auflisten von {path}: {e}")
    return results

# --- Skript Ausführung ---

if __name__ == "__main__":
    config = load_config()
    
    # Zugriff auf die FTP-Daten aus der JSON-Konfiguration
    ftp_config = config['ftp']
    
    test_ftp_connection(
        host=ftp_config['host'],
        user=ftp_config['user'],
        password=ftp_config['pass'],
        port=ftp_config['port']
    )
