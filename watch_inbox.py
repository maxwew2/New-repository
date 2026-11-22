"""Скрипт следит за папкой и записывает в отчёт, какие файлы появились и исчезли.

Запуск:  python watch_inbox.py Входящие
Коды возврата: 0 — проверка выполнена, 3 — папка не найдена.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent   # папка, где лежит скрипт
REPORT = HERE / "Отчёт.txt"              # путь к отчёту — переменная, тест её подменит
STATE = HERE / "Состояние.json"          # список файлов с прошлого запуска


def write_report(folder_name, text):
    with REPORT.open("a", encoding="utf-8") as report:
        report.write(f"{datetime.now():%d.%m.%Y %H:%M} — папка «{folder_name}»\n{text}\n\n")


def load_state():
    """Читает сохранённые списки файлов. Если файла нет или он испорчен — пустой словарь."""
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def list_files(folder):
    """Имена обычных файлов в папке без скрытых (начинающихся с точки)."""
    return sorted(p.name for p in folder.iterdir() if p.is_file() and not p.name.startswith("."))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Какие файлы появились и исчезли в папке.")
    parser.add_argument("folder", help="папка, за которой следим")
    args = parser.parse_args(argv)
    folder = HERE / args.folder          # абсолютный путь остаётся как есть

    if not folder.is_dir():
        write_report(folder.name, "Проверка не удалась: папка не найдена.")
        return 3

    current = list_files(folder)
    state = load_state()
    previous = state.get(folder.name)

    if previous is None:
        text = f"Первая проверка. Файлов в папке: {len(current)}."
    else:
        appeared = [name for name in current if name not in previous]
        vanished = [name for name in previous if name not in current]
        if not appeared and not vanished:
            text = "Ничего не изменилось."
        else:
            lines = []
            if appeared:
                lines.append("Появились: " + ", ".join(appeared))
            if vanished:
                lines.append("Исчезли: " + ", ".join(vanished))
            text = "\n".join(lines)

    write_report(folder.name, text)
    state[folder.name] = current
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
