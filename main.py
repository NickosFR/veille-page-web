"""Point d'entrée. Usage : python main.py [chemin_fichier_maitre]"""

from __future__ import annotations

import logging
import sys

from pipeline import run_master

DEFAULT_MASTER = "InputRules.txt"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    master_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MASTER
    run_master(master_path)


if __name__ == "__main__":
    main()
