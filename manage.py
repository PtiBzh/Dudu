#!/usr/bin/env python
"""Outil de ligne de commande Django pour le projet Dudu."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dudu.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django n'est pas installé dans cet environnement. "
            "Active le venv et lance : pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
