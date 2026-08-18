"""Orchestrateur d'une veille de page(s) web : exécute séquentiellement les commandes
d'un fichier de règles (voir rules.py pour le format, README.md pour la liste des
commandes)."""

from __future__ import annotations

import datetime
import difflib
import logging
import os
from dataclasses import dataclass, field

from feed_builder import write_feed
from rules import parse_rule_file
from sheets_store import append_history_entry, read_history, read_state, write_state_entry
from snapshot_store import append_change, load_history, load_state, make_guid, save_state
from watcher import PageRemovedError, WatchError, fetch_markdown

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITEMS = 50


@dataclass
class VeilleState:
    name: str = "veille"
    path_out: str = "."
    urls: list = field(default_factory=list)
    date_debut: str = ""
    date_fin: str = ""
    max_items: int = DEFAULT_MAX_ITEMS
    sheet_id: str = ""


def _state_file(state: VeilleState) -> str:
    return os.path.join(state.path_out, f"{state.name}_state.json")


def _history_file(state: VeilleState) -> str:
    return os.path.join(state.path_out, f"{state.name}_history.json")


def _feed_file(state: VeilleState) -> str:
    return os.path.join(state.path_out, f"{state.name}.xml")


def _today_allowed(days_spec: str) -> bool:
    """`days_spec` = chiffres collés (ex: '135' = lundi, mercredi, vendredi), 1=lundi...7=dimanche."""
    allowed = {int(c) for c in days_spec if c.isdigit()}
    return not allowed or datetime.date.today().isoweekday() in allowed


def _within_window(state: VeilleState) -> bool:
    today = datetime.date.today().isoformat()
    if state.date_debut and today < state.date_debut:
        return False
    if state.date_fin and today > state.date_fin:
        return False
    return True


def _build_diff(previous_markdown: str, current_markdown: str) -> str:
    diff_lines = difflib.unified_diff(
        (previous_markdown or "").splitlines(),
        (current_markdown or "").splitlines(),
        lineterm="",
    )
    return "\n".join(diff_lines)


def _record_change(state: VeilleState, history_path: str, url: str, now: str, status: str, diff: str) -> None:
    if state.sheet_id:
        guid = make_guid(url, now)
        append_history_entry(
            state.sheet_id, state.name, {"guid": guid, "url": url, "detected_at": now, "status": status, "diff": diff}
        )
    else:
        append_change(history_path, url, now, status, diff)


def _check_url(url: str, state: VeilleState, history_path: str, page_state: dict) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        markdown = fetch_markdown(url)
    except PageRemovedError:
        logger.info("%s : page introuvable (404), ajouté à l'historique.", url)
        _record_change(state, history_path, url, now, "removed", "Page supprimée ou inaccessible.")
        return
    except WatchError:
        logger.exception("Échec de la récupération de %s", url)
        return

    previous = page_state.get(url)
    if previous is None:
        logger.info("%s : première visite, snapshot initial enregistré.", url)
    elif previous == markdown:
        logger.info("%s : aucun changement.", url)
    else:
        diff = _build_diff(previous, markdown)
        _record_change(state, history_path, url, now, "changed", diff)
        logger.info("%s : changement détecté, ajouté à l'historique.", url)

    page_state[url] = markdown
    if state.sheet_id:
        # Écriture immédiate, indépendante des autres URLs de la boucle : si une panne
        # coupe le run avant la fin, cette URL reste acquise dans le Sheet.
        write_state_entry(state.sheet_id, state.name, url, markdown, now)


def run_veille(rules_path: str) -> None:
    state = VeilleState()
    commands = parse_rule_file(rules_path)

    for name, args in commands:
        if name == "Stop":
            break
        elif name == "Name":
            state.name = args[0]
        elif name == "PathOut":
            state.path_out = args[0]
            os.makedirs(state.path_out, exist_ok=True)
        elif name == "Freq":
            if not _today_allowed(args[0]):
                logger.info("Veille %s ignorée aujourd'hui (Freq;%s).", state.name, args[0])
                return
        elif name == "Url":
            state.urls.append(args[0])
        elif name == "DateDebut":
            state.date_debut = args[0]
        elif name == "DateFin":
            state.date_fin = args[0]
        elif name == "MaxItems":
            state.max_items = int(args[0])
        elif name == "SheetId":
            state.sheet_id = args[0]
        else:
            logger.warning("Commande inconnue ignorée : %s %s", name, args)

    if not state.urls:
        logger.warning("Veille %s : aucune Url définie, rien à faire.", state.name)
        return

    if not _within_window(state):
        logger.info(
            "Veille %s hors fenêtre de surveillance (%s → %s), ignorée aujourd'hui.",
            state.name,
            state.date_debut or "sans début",
            state.date_fin or "sans fin",
        )
        return

    history_path = _history_file(state)
    page_state = read_state(state.sheet_id, state.name) if state.sheet_id else load_state(_state_file(state))

    for url in state.urls:
        _check_url(url, state, history_path, page_state)

    if not state.sheet_id:
        # Sauvegarde groupée : chemin local historique, inchangé. Avec un Sheet, chaque
        # ligne est déjà écrite au fil de la boucle dans _check_url, rien à faire ici.
        save_state(_state_file(state), page_state)

    history = read_history(state.sheet_id, state.name) if state.sheet_id else load_history(history_path)
    write_feed(state.name, state.urls[0], history, _feed_file(state), max_items=state.max_items)


def run_master(master_path: str) -> None:
    for name, args in parse_rule_file(master_path):
        if name == "Stop":
            break
        if name != "Exec":
            continue
        try:
            run_veille(args[0])
        except Exception:
            logger.exception("Échec de la veille définie dans %s", args[0])
