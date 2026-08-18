"""Récupère le contenu d'une page web en Markdown, par requête HTTP simple — pas de rendu
JavaScript, pas de dépendance externe payante (choix assumé, 2026-08-18, en remplacement
de Firecrawl : voir CLAUDE.md). Limite acceptée : une page qui construit son contenu en
JavaScript côté navigateur après chargement n'est pas capturée (voir README.md).

La détection de changement (new/same/changed) n'est plus calculée côté fournisseur
externe : c'est pipeline.py qui compare le markdown récupéré ici à l'état précédent.
Seul le cas « page introuvable » (HTTP 404) est distingué ici, via `PageRemovedError`."""

from __future__ import annotations

import requests
from markdownify import markdownify

_TIMEOUT = 30
_USER_AGENT = "Mozilla/5.0 (compatible; veille-page-web/1.0)"


class WatchError(RuntimeError):
    pass


class PageRemovedError(WatchError):
    pass


def fetch_markdown(url: str) -> str:
    try:
        response = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT})
    except requests.RequestException as exc:
        raise WatchError(f"Échec de la requête HTTP pour {url} : {exc}") from exc

    if response.status_code == 404:
        raise PageRemovedError(f"{url} renvoie 404 (page supprimée ou déplacée).")
    if response.status_code >= 400:
        raise WatchError(f"{url} a renvoyé le statut HTTP {response.status_code}.")

    return markdownify(response.text, heading_style="ATX").strip()
