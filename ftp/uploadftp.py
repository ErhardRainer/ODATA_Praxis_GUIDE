import os
import json
from ftplib import FTP

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

# --- Hauptfunktion ---

def upload_directory_recursive(ftp, local_dir, remote_dir):
    """
    Lädt alle Dateien und Unterordner aus local_dir rekursiv in remote_dir hoch.
    (Der Inhalt dieser Funktion bleibt unverändert zum Original-Skript)
    """
    print(f"Starte Upload von: '{local_dir}' nach '{remote_dir}'")
    
    try:
        ftp.mkd(remote_dir)
    except Exception:
        pass

    ftp.cwd(remote_dir)

    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_item = item

        if os.path.isfile(local_path):
            print(f"Lade Datei hoch: {remote_item}...")
            with open(local_path, 'rb') as fp:
                ftp.storbinary(f'STOR {remote_item}', fp)
            print(f"-> {remote_item} erfolgreich hochgeladen.")

        elif os.path.isdir(local_path):
            print(f"Betrete Unterordner: {remote_item}")
            upload_directory_recursive(ftp, local_path, remote_item)
            
    ftp.cwd('..')
    print(f"Upload für '{local_dir}' abgeschlossen.")

# --- Skript Ausführung ---

if __name__ == "__main__":
    config = load_config()

    FTP_HOST = config['ftp']['host']
    FTP_USER = config['ftp']['user']
    FTP_PASS = config['ftp']['pass']
    git_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOCAL_ROOT_DIR = os.path.join(git_root, config['paths']['local_root_dir'])
    REMOTE_ROOT_DIR = config['paths']['remote_root_dir']

    try:
        print(f"Versuche, Verbindung zu {FTP_HOST} herzustellen...")
        
        with FTP(FTP_HOST) as ftp:
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            print("Verbindung erfolgreich hergestellt und angemeldet.")
            
            upload_directory_recursive(ftp, LOCAL_ROOT_DIR, REMOTE_ROOT_DIR)
            
            print("\n*** Alle Dateien erfolgreich hochgeladen! ***")

    except Exception as e:
        print(f"\nEin Fehler ist aufgetreten: {e}")