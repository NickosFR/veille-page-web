"""Lecture des fichiers de règles : format `Commande;arg1;arg2;...`, une instruction
par ligne, commentaires introduits par # (en début de ligne ou après une espace/tabulation)."""

from __future__ import annotations

import re

_COMMENT_RE = re.compile(r"(^|\s)#")


def parse_rule_file(path: str) -> list:
    """Renvoie une liste de tuples (nom_commande, [arguments])."""
    commands = []
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n").rstrip("\r")
            m = _COMMENT_RE.search(line)
            if m:
                line = line[: m.start()]
            line = line.strip()
            if not line:
                continue
            parts = line.split(";")
            name = parts[0].strip()
            args = [p.strip() for p in parts[1:]]
            commands.append((name, args))
    return commands
