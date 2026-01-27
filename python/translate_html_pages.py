"""
--- metadata
schema_version: "1.0"
name: "python.translate_html_pages"
display_name: "HTML Translator (DE -> other langs)"
module_type: "cli"
version: "1.0.0"
status: "stable"
created: "2026-01-27"
updated: "2026-01-27"

author: "Erhard Rainer (ER)"
python: ">=3.11"
dependencies: []

summary: >
  Übersetzt HTML-Dateien (z. B. *_de.html) automatisiert in andere Sprachen
  via OpenAI API (ChatGPT / GPT-5.2) und ersetzt die Ziel-Dateien.

description: |
  Dieses CLI ist dafür gedacht, dass nur die deutsche Variante gepflegt wird.
  Aufrufbar für alle *_de.html unter einem Root oder für eine konkrete Datei.

  Der API-Key wird NICHT im Repo gespeichert, sondern aus einer separaten JSON
  geladen (Home-Verzeichnis empfohlen) oder alternativ über OPENAI_API_KEY.

version_history:
  - line: "1.0.0 2026-01-27 ER Initiale Version: Übersetzen von *_de.html nach Zielsprachen per CLI."
    version: "1.0.0"
    date: "2026-01-27"
    author: "ER"
    description: "Initiale Version: Übersetzen von *_de.html nach Zielsprachen per CLI."
--- end
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = [
    "translate_html_pages",
    "main",
    "__version__",
    "get_version",
]


def get_version() -> str:
    """Gibt die Modulversion zurück (für Reload/Telemetry)."""

    return __version__


import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_LANG_NAME: dict[str, str] = {
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
    "ja": "Japanese",
    "pt": "Portuguese",
    "zh": "Chinese (Simplified)",
}


@dataclass(frozen=True)
class TranslateResult:
    source_file: Path
    target_file: Path
    source_lang: str
    target_lang: str
    written: bool
    skipped_reason: str | None


class OpenAIError(RuntimeError):
    pass


def _default_key_file_candidates() -> list[Path]:
    home = Path.home()

    return [
        # bevorzugt außerhalb des Repos
        home / ".odata_praxis_guide" / "openai_key.json",
        home / ".config" / "odata_praxis_guide" / "openai_key.json",
        # optional, aber per .gitignore auszuschließen
        Path(__file__).resolve().parent / "openai_key.json",
    ]


def _load_openai_api_key(*, api_key_file: str | Path | None) -> str:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key.strip()

    candidates: list[Path] = []
    if api_key_file:
        candidates.append(Path(api_key_file))
    candidates.extend(_default_key_file_candidates())

    for path in candidates:
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise OpenAIError(f"Kann API-Key-Datei nicht lesen: {path} ({exc})") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenAIError(f"Ungültiges JSON in API-Key-Datei: {path} ({exc})") from exc

        key = (
            data.get("openai_api_key")
            or data.get("api_key")
            or data.get("OPENAI_API_KEY")
            or data.get("key")
        )
        if isinstance(key, str) and key.strip():
            return key.strip()

        raise OpenAIError(
            f"API-Key-Datei gefunden ({path}), aber kein Key-Feld. Erwartet z. B. openai_api_key."
        )

    raise OpenAIError(
        "Kein OpenAI API-Key gefunden. Setze OPENAI_API_KEY oder lege eine JSON Datei an "
        "(z. B. ~/.odata_praxis_guide/openai_key.json)."
    )


def _extract_language_codes_from_repo(*, root: Path) -> set[str]:
    pattern = re.compile(r"_([a-z]{2,3})\\.html$", re.IGNORECASE)
    langs: set[str] = set()
    for file in root.rglob("*.html"):
        m = pattern.search(file.name)
        if not m:
            continue
        langs.add(m.group(1).lower())
    return langs


def _parse_target_langs(value: str, *, root: Path, source_lang: str) -> list[str]:
    v = value.strip().lower()
    if v in {"all", "*"}:
        langs = sorted(_extract_language_codes_from_repo(root=root))
        langs = [l for l in langs if l != source_lang]
        if langs:
            return langs
        # fallback: bekannte Standardsprachen
        return [l for l in _LANG_NAME.keys() if l != source_lang]

    parts = [p.strip().lower() for p in v.split(",") if p.strip()]
    # dedupe, stable
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        if p == source_lang:
            continue
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out


def _compute_target_path(source_file: Path, *, source_lang: str, target_lang: str) -> Path:
    suffix = f"_{source_lang}"
    if not source_file.stem.lower().endswith(suffix.lower()):
        raise ValueError(f"Quelle muss auf _{source_lang}.html enden: {source_file.name}")

    base = source_file.stem[: -len(suffix)]
    return source_file.with_name(f"{base}_{target_lang}{source_file.suffix}")


def _build_translation_prompt(*, source_lang: str, target_lang: str) -> str:
    source_name = _LANG_NAME.get(source_lang.lower(), source_lang)
    target_name = _LANG_NAME.get(target_lang.lower(), target_lang)

    return (
        "Du bist ein professioneller Übersetzer für Websites. "
        "Übersetze den folgenden HTML-Inhalt präzise.\n\n"
        f"Quelle: {source_name} ({source_lang})\n"
        f"Ziel: {target_name} ({target_lang})\n\n"
        "WICHTIG:\n"
        "- Gib NUR den übersetzten HTML-Text zurück (kein Markdown, keine Erklärungen).\n"
        "- Erhalte die HTML-Struktur exakt (Tags, Attribute, Klassen, IDs, Reihenfolge).\n"
        "- Übersetze ausschließlich sichtbaren Text (Textknoten) und sinnvolle Attribute wie title/aria-label, "
        "  aber ändere keine URLs, keine Dateinamen, keine CSS-Klassen, keine JS-Keys.\n"
        "- Behalte Entities/Unicode so, dass das Ergebnis gültiges UTF-8 HTML ist.\n"
    )


def _openai_translate_html(
    *,
    api_key: str,
    model: str,
    source_lang: str,
    target_lang: str,
    html: str,
    timeout_s: float,
) -> str:
    url = "https://api.openai.com/v1/responses"
    prompt = _build_translation_prompt(source_lang=source_lang, target_lang=target_lang)

    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Antworte strikt ohne Markdown und ohne Zusatztext.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "text", "text": html},
                ],
            },
        ],
        # leicht konservativ, damit Struktur stabil bleibt
        "temperature": 0.2,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<no body>"
        raise OpenAIError(f"OpenAI HTTPError {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise OpenAIError(f"OpenAI URLError: {exc}") from exc

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenAIError(f"Ungültige JSON Response von OpenAI: {exc}") from exc

    # Robust: erst output_text, sonst output[*].content[*].text
    out_text = obj.get("output_text")
    if isinstance(out_text, str) and out_text.strip():
        return out_text.strip()

    parts: list[str] = []
    output = obj.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                t = c.get("type")
                text = c.get("text")
                if isinstance(text, str) and text.strip() and t in {"output_text", "text"}:
                    parts.append(text)

    merged = "".join(parts).strip()
    if merged:
        return merged

    raise OpenAIError("Konnte keinen Text aus der OpenAI Response extrahieren.")


def _write_file_with_backup(
    *, target: Path, content: str, encoding: str, backup: bool, dry_run: bool
) -> bool:
    if dry_run:
        return False

    target.parent.mkdir(parents=True, exist_ok=True)

    if backup and target.exists():
        backup_path = target.with_suffix(target.suffix + ".bak")
        backup_path.write_text(target.read_text(encoding=encoding), encoding=encoding)

    target.write_text(content, encoding=encoding)
    return True


def translate_html_pages(
    *,
    root: str | Path,
    source_lang: str = "de",
    target_langs: Iterable[str] = ("en", "es", "fr"),
    file: str | Path | None = None,
    model: str = "gpt-5.2",
    api_key_file: str | Path | None = None,
    timeout_s: float = 60.0,
    dry_run: bool = True,
    backup: bool = True,
    rate_limit_s: float = 0.0,
) -> list[TranslateResult]:
    """
    --- entrypoint
    name: "translate_html_pages"
    summary: "Übersetzt *_de.html (oder eine konkrete Datei) in Zielsprachen und ersetzt die Ziel-HTML-Dateien."
    params:
      - name: "root"
        type: "Path|str"
        default: null
        desc: "Root-Verzeichnis, unter dem nach HTML-Dateien gesucht wird (z. B. Website/content)."
      - name: "source_lang"
        type: "str"
        default: "de"
        desc: "Quellsprache als Suffix-Code (z. B. de in *_de.html)."
      - name: "target_langs"
        type: "Iterable[str]"
        default: "('en','es','fr')"
        desc: "Zielsprachen als Liste/Codes (z. B. ['en','fr'])."
      - name: "file"
        type: "Path|str|None"
        default: null
        desc: "Optional: konkrete Quell-Datei statt Scan über root (muss auf _<source_lang>.html enden)."
      - name: "model"
        type: "str"
        default: "gpt-5.2"
        desc: "OpenAI Modellname (z. B. gpt-5.2)."
      - name: "api_key_file"
        type: "Path|str|None"
        default: null
        desc: "Optionaler Pfad zur JSON-Datei mit openai_api_key. Wenn leer: Default-Candidates oder OPENAI_API_KEY."
      - name: "timeout_s"
        type: "float"
        default: 60.0
        desc: "HTTP Timeout je Request (Sekunden)."
      - name: "dry_run"
        type: "bool"
        default: true
        desc: "Wenn true: nichts schreiben, nur planen/ausgeben."
      - name: "backup"
        type: "bool"
        default: true
        desc: "Wenn true: vor Überschreiben eine .bak Datei anlegen."
      - name: "rate_limit_s"
        type: "float"
        default: 0.0
        desc: "Optionales Sleep zwischen Requests (Sekunden), um Rate Limits zu vermeiden."
    returns:
      - type: "list[TranslateResult]"
        desc: "Liste der Ergebnisse (geschrieben/übersprungen + Zielpfad)."
    --- end
    """

    root_path = Path(root).resolve()
    source_lang = source_lang.strip().lower()
    target_langs_list = [t.strip().lower() for t in target_langs if t.strip()]

    api_key = _load_openai_api_key(api_key_file=api_key_file)

    source_files: list[Path]
    if file is not None:
        f = Path(file).resolve()
        source_files = [f]
    else:
        source_files = sorted(root_path.rglob(f"*_{source_lang}.html"))

    results: list[TranslateResult] = []

    for source_file in source_files:
        if not source_file.exists():
            raise FileNotFoundError(str(source_file))

        html = source_file.read_text(encoding="utf-8")

        for target_lang in target_langs_list:
            target_file = _compute_target_path(
                source_file, source_lang=source_lang, target_lang=target_lang
            )

            translated = _openai_translate_html(
                api_key=api_key,
                model=model,
                source_lang=source_lang,
                target_lang=target_lang,
                html=html,
                timeout_s=timeout_s,
            )

            if not translated.strip().startswith("<"):
                raise OpenAIError(
                    f"Übersetzung wirkt nicht wie HTML ({source_file.name} -> {target_file.name})."
                )

            written = _write_file_with_backup(
                target=target_file,
                content=translated,
                encoding="utf-8",
                backup=backup,
                dry_run=dry_run,
            )

            results.append(
                TranslateResult(
                    source_file=source_file,
                    target_file=target_file,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    written=written,
                    skipped_reason=None if written else "dry-run",
                )
            )

            if rate_limit_s > 0:
                time.sleep(rate_limit_s)

    return results


def main(argv: list[str] | None = None) -> int:
    """
    --- entrypoint
    name: "main"
    summary: "CLI Entry-Point: Übersetzt *_de.html oder eine Datei in Zielsprachen und schreibt Ziel-Dateien."
    params:
      - name: "argv"
        type: "list[str]|None"
        default: null
        desc: "Optional: Argumente (für Tests). Wenn None: sys.argv[1:]."
    returns:
      - type: "int"
        desc: "Exit-Code (0 ok, !=0 Fehler)."
    --- end
    """

    p = argparse.ArgumentParser(
        prog="translate_html_pages",
        description=(
            "Übersetzt *_de.html (oder eine konkrete Datei) in Zielsprachen via OpenAI und ersetzt die Ziel-Dateien."
        ),
    )

    p.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1] / "Website" / "content"),
        help="Root zum Scannen (Default: Website/content im Repo)",
    )
    p.add_argument(
        "--file",
        default=None,
        help="Optional: konkrete Quell-Datei (muss auf _<source_lang>.html enden)",
    )
    p.add_argument("--source-lang", default="de", help="Quellsprache (Suffix), z. B. de")
    p.add_argument(
        "--target-langs",
        default="all",
        help="Zielsprachen: 'all' oder z. B. 'en,fr,es'",
    )
    p.add_argument(
        "--target-lang",
        default=None,
        help="Einzelne Zielsprache (Shortcut; überschreibt --target-langs)",
    )
    p.add_argument(
        "--model",
        default="gpt-5.2",
        help="OpenAI Modell (Default: gpt-5.2)",
    )
    p.add_argument(
        "--api-key-file",
        default=None,
        help="Pfad zur JSON-Datei mit openai_api_key (optional; sonst OPENAI_API_KEY oder Default-Pfade)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP Timeout pro Request (Sekunden)",
    )
    p.add_argument(
        "--rate-limit",
        type=float,
        default=0.0,
        help="Sleep zwischen Requests (Sekunden)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Schreibt die Ziel-Dateien (sonst default: dry-run)",
    )
    p.add_argument(
        "--no-backup",
        action="store_true",
        help="Kein .bak Backup beim Überschreiben",
    )

    args = p.parse_args(argv)

    try:
        root_path = Path(args.root).resolve()
        source_lang = str(args.source_lang).strip().lower()
        target_spec = args.target_lang if args.target_lang else args.target_langs
        target_langs = _parse_target_langs(target_spec, root=root_path, source_lang=source_lang)

        if not target_langs:
            raise ValueError("Keine Zielsprachen angegeben/ermittelt.")

        results = translate_html_pages(
            root=root_path,
            source_lang=source_lang,
            target_langs=target_langs,
            file=args.file,
            model=args.model,
            api_key_file=args.api_key_file,
            timeout_s=float(args.timeout),
            dry_run=not bool(args.apply),
            backup=not bool(args.no_backup),
            rate_limit_s=float(args.rate_limit),
        )

        written = sum(1 for r in results if r.written)
        planned = len(results)
        print(f"OK: {planned} Übersetzungen, geschrieben: {written}")
        if not args.apply:
            print("Hinweis: dry-run. Mit --apply werden Dateien geschrieben.")

        for r in results:
            action = "WRITE" if r.written else "PLAN"
            print(
                f"{action}: {r.source_file.relative_to(root_path)} -> {r.target_file.relative_to(root_path)}"
            )

        return 0

    except Exception as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
