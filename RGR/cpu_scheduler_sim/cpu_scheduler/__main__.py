"""Запуск пакета як модуля: python -m cpu_scheduler <команда> ..."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
