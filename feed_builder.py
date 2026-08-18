"""Construction du flux RSS à partir de l'historique des changements détectés (fichiers
JSON locaux via snapshot_store.py, ou Google Sheet via sheets_store.py selon la veille —
la source de l'historique est décidée par l'appelant, ce module n'en dépend pas). Le flux
est régénéré en entier à chaque exécution à partir de l'historique complet, tronqué aux
`max_items` changements les plus récents — l'historique complet, lui, garde tout, le flux
RSS n'en est qu'une vue récente."""

from __future__ import annotations

import datetime

from feedgen.feed import FeedGenerator

_DIFF_MAX_CHARS = 2000


def write_feed(name: str, site_url: str, history: list, feed_path: str, max_items: int = 50) -> None:
    recent = history[-max_items:]

    fg = FeedGenerator()
    fg.id(name)
    fg.title(f"Veille — {name}")
    fg.description(f"Changements détectés sur les pages surveillées par la veille « {name} ».")
    fg.link(href=site_url, rel="alternate")
    fg.language("fr")

    # feedgen.add_entry() insère par défaut en tête de liste (order="prepend") : parcourir
    # `recent` en ordre chronologique croissant fait donc atterrir le changement le plus
    # récent en premier dans le flux généré, convention RSS habituelle.
    for entry in recent:
        fe = fg.add_entry()
        fe.id(entry["guid"])
        fe.guid(entry["guid"], permalink=False)
        fe.title(f"Changement détecté sur {entry['url']}")
        fe.link(href=entry["url"])
        fe.pubDate(datetime.datetime.fromisoformat(entry["detected_at"]))
        summary = entry["diff"][:_DIFF_MAX_CHARS] if entry["diff"] else "(page supprimée ou inaccessible)"
        fe.description(f"<pre>{summary}</pre>")

    fg.rss_file(feed_path)
