"""Client Google Sheets (via gspread) : persistance optionnelle de l'état par URL et de
l'historique des changements, en remplacement des fichiers JSON locaux (snapshot_store.py)
pour une veille qui déclare `SheetId;<id>`.

Différence délibérée avec les fichiers locaux : chaque ligne (état d'une URL, entrée
d'historique) est écrite immédiatement via l'API Sheets, au fil du traitement de chaque
URL — pas accumulée en mémoire pour une sauvegarde groupée en fin de run. Si une page
tombe en erreur (timeout, HTTP 5xx) ou que le job plante en cours de route, les URLs déjà
traitées avant l'incident restent acquises dans le Sheet ; avec les fichiers JSON locaux,
tout dépend du commit git de fin de run (voir .github/workflows/veille-page.yml), qui n'a
jamais lieu si le run s'arrête avant la fin.

Même pattern d'authentification que projets/veille-emploi/python/sheets_client.py (compte
de service Google Cloud, JSON en variable d'environnement) — copié plutôt qu'importé
car chaque projet est déployé dans son propre dépôt git, sans dépendance croisée."""

from __future__ import annotations

import json
import os
from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_CREDENTIALS_VAR = "VEILLE_PAGE_WEB_GOOGLE_CREDENTIALS"

_STATE_HEADER = ["key", "veille", "url", "markdown", "updated_at"]
_HISTORY_HEADER = ["veille", "guid", "url", "detected_at", "status", "diff"]


class SheetsConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _client() -> gspread.Client:
    raw = os.environ.get(_CREDENTIALS_VAR)
    if not raw:
        raise SheetsConfigError(f"Variable d'environnement {_CREDENTIALS_VAR} manquante (JSON du compte de service).")
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    return gspread.authorize(creds)


def _worksheet(sheet_id: str, tab_name: str, header: list) -> gspread.Worksheet:
    sheet = _client().open_by_key(sheet_id)
    try:
        return sheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet(tab_name, rows=1, cols=len(header))
        worksheet.append_row(header, value_input_option="USER_ENTERED")
        return worksheet


def read_state(sheet_id: str, veille_name: str) -> dict:
    """Renvoie {url: markdown} pour les entrées déjà connues de `veille_name`."""
    worksheet = _worksheet(sheet_id, "state", _STATE_HEADER)
    return {r["url"]: r["markdown"] for r in worksheet.get_all_records() if r.get("veille") == veille_name}


def write_state_entry(sheet_id: str, veille_name: str, url: str, markdown: str, updated_at: str) -> None:
    """Insère ou met à jour la ligne (veille, url) — écriture immédiate et indépendante des
    autres URLs de la même veille."""
    worksheet = _worksheet(sheet_id, "state", _STATE_HEADER)
    header = worksheet.row_values(1) or _STATE_HEADER
    key = f"{veille_name}|{url}"
    key_col = header.index("key") + 1
    existing_keys = worksheet.col_values(key_col)[1:]
    row = [key, veille_name, url, markdown, updated_at]
    if key in existing_keys:
        row_index = existing_keys.index(key) + 2
        worksheet.update(f"A{row_index}", [row])
    else:
        worksheet.append_row(row, value_input_option="USER_ENTERED")


def read_history(sheet_id: str, veille_name: str) -> list:
    worksheet = _worksheet(sheet_id, "history", _HISTORY_HEADER)
    return [r for r in worksheet.get_all_records() if r.get("veille") == veille_name]


def append_history_entry(sheet_id: str, veille_name: str, entry: dict) -> None:
    worksheet = _worksheet(sheet_id, "history", _HISTORY_HEADER)
    row = [veille_name, entry["guid"], entry["url"], entry["detected_at"], entry["status"], entry["diff"]]
    worksheet.append_row(row, value_input_option="USER_ENTERED")
