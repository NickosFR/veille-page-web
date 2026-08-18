"""Persistance locale au format JSON, en deux parties. Utilisée quand une veille ne
déclare pas `SheetId` (voir sheets_store.py pour l'alternative Google Sheets).

- État par URL (`load_state`/`save_state`) : dernier markdown récupéré pour chaque page,
  utilisé pour calculer le diff local lors du prochain changement détecté (voir
  pipeline.py — la comparaison au run précédent se fait toujours en local, watcher.py ne
  fait que récupérer le markdown courant).
- Historique des changements (`load_history`/`save_history`/`append_change`) :
  append-only, une entrée par changement détecté, source de vérité du flux RSS.

En exécution cloud (GitHub Actions), le répertoire de travail est effacé à la fin de
chaque run : ces fichiers doivent être recommités dans le dépôt par le workflow pour
survivre au run suivant (voir .github/workflows/veille-page.yml).

C'est cet historique daté qui répond au besoin de fenêtre "entre deux dates" : seule la
comparaison contre le dernier run est possible autrement, jamais entre deux dates
arbitraires. Chaque changement détecté est donc accumulé ici avec sa date, et c'est ce
store qui permet de reconstituer/filtrer l'historique.
"""

from __future__ import annotations

import hashlib
import json
import os


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_history(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_history(path: str, history: list) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def make_guid(url: str, detected_at: str) -> str:
    return hashlib.sha256(f"{url}|{detected_at}".encode("utf-8")).hexdigest()[:16]


def append_change(path: str, url: str, detected_at: str, status: str, diff: str) -> dict:
    """Ajoute une entrée à l'historique et le sauvegarde. `status` = 'changed' ou 'removed'."""
    history = load_history(path)
    entry = {
        "guid": make_guid(url, detected_at),
        "url": url,
        "detected_at": detected_at,
        "status": status,
        "diff": diff,
    }
    history.append(entry)
    save_history(path, history)
    return entry
