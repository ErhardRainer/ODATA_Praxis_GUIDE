"""
--- metadata
schema_version: "1.0"
name: "python.create_languages"
display_name: "Create Missing Language Pages"
module_type: "cli"
version: "1.0.0"
status: "stable"
created: "2026-01-27"
updated: "2026-01-27"

author: "Erhard Rainer (ER)"
python: ">=3.11"
dependencies: []

summary: >
  Stellt sicher, dass unter Website/content für jede Seite alle Sprachvarianten
  als *_<lang>.html existieren. Fehlen Varianten, werden sie aus DE kopiert.

description: |
  Dieses Script iteriert rekursiv über alle HTML-Dateien unterhalb eines
  Content-Roots. Für Seiten ohne Sprachsuffix (z. B. docs/allg/ben.html) wird
  die Datei in die DE-Variante umbenannt (ben_de.html). Anschließend werden
  fehlende Sprachdateien (ben_en.html, ...) als Kopien erzeugt.

  Wichtig: Es findet KEINE Übersetzung statt, sondern nur Datei-Operationen.

version_history:
  - line: "1.0.0 2026-01-27 ER Initiale Version: Umbenennen nach *_de.html und Kopieren fehlender Sprachdateien."
    version: "1.0.0"
    date: "2026-01-27"
    author: "ER"
    description: "Initiale Version: Umbenennen nach *_de.html und Kopieren fehlender Sprachdateien."
--- end
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = [
    "create_missing_language_pages",
    "main",
    "REQUIRED_LANGS",
    "__version__",
    "get_version",
]


def get_version() -> str:
    """Gibt die Modulversion zurück (für Reload/Telemetry)."""

    return __version__


import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


# Hier die notwendigen Sprachen pflegen.
REQUIRED_LANGS: list[str] = ["de", "en", "fr", "es", "pt", "ja", "zh", "hi"]


@dataclass(frozen=True)
class Operation:
    kind: str  # RENAME | COPY | NAV | SKIP | WARN
    source: Path | None
    target: Path | None
    message: str


def _parse_lang_suffix(file: Path, *, required_langs: set[str]) -> tuple[str, str | None]:
    """Gibt (base_stem, lang) zurück, wobei lang None bedeutet: keine Sprachvariante."""

    stem = file.stem
    lower = stem.lower()
    for lang in required_langs:
        suffix = f"_{lang}"
        if lower.endswith(suffix):
            return stem[: -len(suffix)], lang
    return stem, None


def _expected_lang_file(file: Path, *, base_stem: str, lang: str) -> Path:
    return file.with_name(f"{base_stem}_{lang}{file.suffix}")


def _path_to_posix(path: Path) -> str:
    return "/".join(path.parts)


def _strip_html_lang_suffix(path_str: str, *, required_langs: set[str]) -> tuple[str, str | None]:
    """Für 'content/.../x_de.html' -> ('content/.../x', 'de'); sonst ('.../x', None)."""

    p = Path(path_str)
    stem = p.stem
    lower = stem.lower()
    for lang in required_langs:
        suffix = f"_{lang}"
        if lower.endswith(suffix):
            base_stem = stem[: -len(suffix)]
            base = p.with_name(base_stem).with_suffix("")
            return _path_to_posix(base), lang
    return _path_to_posix(p.with_suffix("")), None


def _build_files_mapping_from_path(
    path_str: str,
    *,
    required_langs: list[str],
) -> dict[str, str]:
    """Erzeugt {lang: 'content/.../base_lang.html'} anhand eines Content-Pfads."""

    required_set = set(required_langs)
    p = Path(path_str)
    if p.suffix.lower() != ".html":
        raise ValueError(f"Nur .html wird unterstützt: {path_str}")

    # Base ermitteln: entweder unsuffixed oder suffixed.
    base_noext, _ = _strip_html_lang_suffix(path_str, required_langs=required_set)
    base_path = Path(base_noext)

    mapping: dict[str, str] = {}
    for lang in required_langs:
        target = base_path.with_name(f"{base_path.name}_{lang}").with_suffix(".html")
        mapping[lang] = _path_to_posix(target)

    return mapping


def _update_navigation_obj(
    obj: object,
    *,
    required_langs: list[str],
    changed: list[tuple[str, str]],
) -> object:
    """Rekursiv: konvertiert {file: 'content/.../x.html'} -> {files: {de:..., ...}}.

    changed: sammelt (old_file, new_files_de) für Reporting.
    """

    required_set = set(required_langs)

    if isinstance(obj, list):
        return [
            _update_navigation_obj(i, required_langs=required_langs, changed=changed)
            for i in obj
        ]

    if not isinstance(obj, dict):
        return obj

    # Erst children aktualisieren
    new_items: list[tuple[str, object]] = []
    for k, v in obj.items():
        if k in {"file", "files"}:
            # später behandeln
            continue
        new_items.append(
            (k, _update_navigation_obj(v, required_langs=required_langs, changed=changed))
        )

    has_files = "files" in obj and isinstance(obj.get("files"), dict)
    has_file = "file" in obj and isinstance(obj.get("file"), str)

    if has_files:
        existing: dict[str, object] = obj["files"]  # type: ignore[assignment]
        # Basis aus de oder erstem Eintrag ableiten
        sample = None
        if isinstance(existing.get("de"), str):
            sample = existing.get("de")
        else:
            for vv in existing.values():
                if isinstance(vv, str):
                    sample = vv
                    break

        if isinstance(sample, str) and sample.startswith("content/") and sample.lower().endswith(".html"):
            full = _build_files_mapping_from_path(sample, required_langs=required_langs)
            merged: dict[str, str] = {}
            for lang in required_langs:
                val = existing.get(lang)
                if isinstance(val, str) and val:
                    merged[lang] = val
                else:
                    merged[lang] = full[lang]

            # 'files' nachbilden (mit stabiler Reihenfolge REQUIRED_LANGS)
            new_items.append(("files", merged))
        else:
            # nichts tun, aber children bereits aktualisiert
            new_items.append(("files", existing))

        # evtl. sonstige keys aus obj, die wir übersprungen haben, wieder anhängen
        for k, v in obj.items():
            if k in {"file", "files"}:
                continue
            # bereits in new_items
        return dict(new_items)

    if has_file:
        file_path = str(obj["file"])
        if file_path.startswith("content/") and file_path.lower().endswith(".html"):
            mapping = _build_files_mapping_from_path(file_path, required_langs=required_langs)
            new_items.append(("files", mapping))
            changed.append((file_path, mapping.get("de", "")))
            return dict(new_items)

    # Default: original dict mit children-updates, plus original file/files (unverändert), falls vorhanden
    if has_file:
        new_items.append(("file", obj["file"]))
    if "files" in obj:
        new_items.append(("files", obj["files"]))

    return dict(new_items)


def update_navigation_json(
    *,
    navigation_json: str | Path,
    required_langs: list[str],
    dry: bool,
) -> list[Operation]:
    path = Path(navigation_json).resolve()
    if not path.exists():
        return [
            Operation(
                kind="WARN",
                source=None,
                target=path,
                message="navigation.json nicht gefunden; kein Update durchgeführt.",
            )
        ]

    raw = path.read_text(encoding="utf-8")
    obj = json.loads(raw)
    changed: list[tuple[str, str]] = []
    updated = _update_navigation_obj(obj, required_langs=required_langs, changed=changed)

    if not changed:
        return [
            Operation(
                kind="SKIP",
                source=path,
                target=path,
                message="navigation.json bereits ok (keine 'file'->'files' Konvertierung nötig).",
            )
        ]

    ops: list[Operation] = []
    ops.append(
        Operation(
            kind="NAV",
            source=path,
            target=path,
            message=f"Konvertiert {len(changed)} Einträge von 'file' auf 'files' (i18n-Mapping).",
        )
    )
    for old, de in changed[:10]:
        ops.append(
            Operation(
                kind="NAV",
                source=None,
                target=None,
                message=f"file: {old} -> files.de: {de}",
            )
        )
    if len(changed) > 10:
        ops.append(
            Operation(
                kind="NAV",
                source=None,
                target=None,
                message=f"... weitere {len(changed) - 10} Einträge",
            )
        )

    if not dry:
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return ops


def create_missing_language_pages(
    *,
    root: str | Path,
    dry: bool = True,
) -> list[Operation]:
    """
    --- entrypoint
    name: "create_missing_language_pages"
    summary: "Erzwingt *_<lang>.html pro Seite: ben.html -> ben_de.html und kopiert fehlende Sprachdateien."
    params:
      - name: "root"
        type: "Path|str"
        default: null
        desc: "Content-Root (z. B. Website/content)."
      - name: "dry"
        type: "bool"
        default: true
        desc: "Dry-Run: keine Dateisystemänderungen, nur Operationen ausgeben."
    returns:
      - type: "list[Operation]"
        desc: "Liste der geplanten/ausgeführten Operationen."
    --- end
    """

    root_path = Path(root).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise FileNotFoundError(str(root_path))

    required = [l.strip().lower() for l in REQUIRED_LANGS if l.strip()]
    required_set = set(required)

    # Gruppe pro "Seite" (Ordner + base_stem)
    groups: dict[tuple[Path, str, str], dict[str, Path]] = {}
    # key: (parent_dir, base_stem, ext)

    for file in root_path.rglob("*.html"):
        if not file.is_file():
            continue

        base_stem, lang = _parse_lang_suffix(file, required_langs=required_set)
        key = (file.parent, base_stem, file.suffix.lower())
        entry = groups.setdefault(key, {})

        if lang is None:
            entry["__base__"] = file
        else:
            entry[lang] = file

    ops: list[Operation] = []

    for (parent_dir, base_stem, ext), files in sorted(groups.items(), key=lambda x: (str(x[0][0]), x[0][1])):
        base_file = files.get("__base__")
        de_file = files.get("de")
        de_source_for_copy: Path | None = de_file

        # Wenn es eine unsuffixed Datei gibt, soll die zu *_de.html werden.
        if base_file is not None:
            desired_de = parent_dir / f"{base_stem}_de{ext}"

            if desired_de.exists() and desired_de != base_file:
                ops.append(
                    Operation(
                        kind="WARN",
                        source=base_file,
                        target=desired_de,
                        message=(
                            "Konflikt: unsuffixed Datei existiert, aber *_de.html existiert bereits. "
                            "Kein Rename durchgeführt."
                        ),
                    )
                )
                # In diesem Fall bleibt die DE-Datei die Quelle (falls vorhanden).
                de_source_for_copy = de_file
            else:
                ops.append(
                    Operation(
                        kind="RENAME",
                        source=base_file,
                        target=desired_de,
                        message="Rename unsuffixed -> de",
                    )
                )
                # In allen Fällen ist die logische DE-Quelle das *_de.html (auch im Dry-Run).
                de_file = desired_de
                de_source_for_copy = desired_de
                if not dry:
                    base_file.rename(desired_de)

        # Quelle für Kopien muss existieren.
        if de_source_for_copy is None or not de_source_for_copy.exists():
            # Fallback: wenn keine DE-Datei da ist, aber irgendeine Sprache existiert, warnen.
            any_lang = next((p for k, p in files.items() if k not in {"__base__"}), None)
            if any_lang is not None:
                ops.append(
                    Operation(
                        kind="WARN",
                        source=any_lang,
                        target=None,
                        message=(
                            "Keine DE-Quelle gefunden; fehlende Sprachen werden NICHT erzeugt. "
                            "Erwartet *_de.html oder eine unsuffixed Datei."
                        ),
                    )
                )
            continue

        # Fehlende Sprachdateien aus DE kopieren.
        for lang in required:
            expected = parent_dir / f"{base_stem}_{lang}{ext}"
            if expected.exists():
                continue
            if lang == "de":
                # de muss existieren (s.o.)
                continue

            ops.append(
                Operation(
                    kind="COPY",
                    source=de_source_for_copy,
                    target=expected,
                    message=f"Kopieren aus DE -> {lang}",
                )
            )
            if not dry:
                shutil.copy2(de_source_for_copy, expected)

    return ops


def main(argv: list[str] | None = None) -> int:
    """
    --- entrypoint
    name: "main"
    summary: "CLI Entry-Point: prüft/erzeugt Sprachdateien unter content (Rename + Copy), optional dry-run."
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
        prog="create_languages",
        description=(
            "Iteriert über Website/content und stellt *_<lang>.html pro Seite sicher. "
            "Unsuffixed Dateien werden zu *_de.html umbenannt; fehlende Sprachen werden aus DE kopiert."
        ),
    )

    default_root = Path(__file__).resolve().parents[1] / "Website" / "content"

    p.add_argument(
        "--root",
        default=str(default_root),
        help="Content-Root (Default: Website/content im Repo)",
    )

    p.add_argument(
        "-dry",
        action="store_true",
        help="Dry-Run (default): keine Änderungen, nur Ausgabe",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Änderungen wirklich durchführen (Rename/Copy)",
    )

    p.add_argument(
        "--update-navigation",
        action="store_true",
        help="Aktualisiert Website/navigation.json: 'file' wird zu 'files' (pro REQUIRED_LANGS).",
    )
    p.add_argument(
        "--no-update-navigation",
        action="store_true",
        help="Deaktiviert das Navigation-Update.",
    )
    p.add_argument(
        "--navigation",
        default=str(Path(__file__).resolve().parents[1] / "Website" / "navigation.json"),
        help="Pfad zu Website/navigation.json (Default: Website/navigation.json im Repo)",
    )

    args = p.parse_args(argv)

    # Default ist dry, außer --apply wurde gesetzt.
    dry = True
    if args.apply:
        dry = False
    if args.dry:
        dry = True

    try:
        ops = create_missing_language_pages(root=args.root, dry=dry)

        # Navigation-Update: Default = an (außer explizit ausgeschaltet)
        do_nav = True
        if args.no_update_navigation:
            do_nav = False
        if args.update_navigation:
            do_nav = True

        if do_nav:
            nav_ops = update_navigation_json(
                navigation_json=args.navigation,
                required_langs=[l.strip().lower() for l in REQUIRED_LANGS if l.strip()],
                dry=dry,
            )
            ops.extend(nav_ops)

        rename_count = sum(1 for o in ops if o.kind == "RENAME")
        copy_count = sum(1 for o in ops if o.kind == "COPY")
        nav_count = sum(1 for o in ops if o.kind == "NAV")
        warn_count = sum(1 for o in ops if o.kind == "WARN")

        mode = "DRY" if dry else "APPLY"
        print(
            f"{mode}: rename={rename_count}, copy={copy_count}, nav={nav_count}, warnings={warn_count}"
        )

        root_path = Path(args.root).resolve()
        for o in ops:
            if o.kind in {"RENAME", "COPY"}:
                src = str(o.source.relative_to(root_path)) if o.source else "-"
                dst = str(o.target.relative_to(root_path)) if o.target else "-"
                print(f"{o.kind}: {src} -> {dst} | {o.message}")
            elif o.kind == "NAV":
                print(f"NAV: {o.message}")
            elif o.kind == "WARN":
                src = str(o.source.relative_to(root_path)) if o.source else "-"
                dst = str(o.target.relative_to(root_path)) if o.target else "-"
                print(f"WARN: {src} -> {dst} | {o.message}")

        return 0
    except Exception as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
