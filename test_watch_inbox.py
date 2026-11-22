"""Автоматические тесты для watch_inbox.py.

Запуск (в папке, где лежат оба файла):
    python -m unittest -v
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import watch_inbox


class WatchInboxTest(unittest.TestCase):

    def setUp(self):
        """Перед КАЖДЫМ тестом: чистая временная папка, отчёт и состояние — тоже во временной."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)

        self.folder = root / "Входящие"
        self.folder.mkdir()

        self.report = root / "Отчёт.txt"
        self.state = root / "Состояние.json"
        for name, path in (("REPORT", self.report), ("STATE", self.state)):
            patch = mock.patch.object(watch_inbox, name, path)
            patch.start()
            self.addCleanup(patch.stop)

    def run_script(self, folder=None):
        """Запускает скрипт как «python watch_inbox.py <папка>».
        Возвращает код возврата и весь текст отчёта."""
        code = watch_inbox.main([str(folder or self.folder)])
        text = self.report.read_text(encoding="utf-8") if self.report.exists() else ""
        return code, text

    def add(self, name):
        (self.folder / name).write_text("текст", encoding="utf-8")

    # --- Тесты ---

    def test_first_run_counts_files(self):
        self.add("Пример.txt")
        self.add("заметки.txt")
        code, text = self.run_script()
        self.assertEqual(code, 0)
        self.assertIn("Первая проверка. Файлов в папке: 2.", text)

    def test_first_run_empty_folder(self):
        code, text = self.run_script()
        self.assertEqual(code, 0)
        self.assertIn("Первая проверка. Файлов в папке: 0.", text)

    def test_nothing_changed(self):
        self.add("Пример.txt")
        self.run_script()
        code, text = self.run_script()
        self.assertEqual(code, 0)
        self.assertIn("Ничего не изменилось.", text)

    def test_new_file_appeared(self):
        self.add("Пример.txt")
        self.run_script()
        self.add("договор.docx")
        _, text = self.run_script()
        self.assertIn("Появились: договор.docx", text)
        self.assertNotIn("Исчезли", text)

    def test_file_vanished(self):
        self.add("Пример.txt")
        self.add("договор.docx")
        self.run_script()
        (self.folder / "Пример.txt").unlink()
        _, text = self.run_script()
        self.assertIn("Исчезли: Пример.txt", text)
        self.assertNotIn("Появились", text)

    def test_appeared_and_vanished_together(self):
        self.add("Пример.txt")
        self.run_script()
        (self.folder / "Пример.txt").unlink()
        self.add("договор.docx")
        _, text = self.run_script()
        self.assertIn("Появились: договор.docx", text)
        self.assertIn("Исчезли: Пример.txt", text)

    def test_change_is_reported_only_once(self):
        self.run_script()
        self.add("договор.docx")
        self.run_script()
        _, text = self.run_script()
        self.assertEqual(text.count("Появились: договор.docx"), 1)
        self.assertTrue(text.rstrip().endswith("Ничего не изменилось."))

    def test_hidden_files_are_ignored(self):
        self.run_script()
        (self.folder / ".DS_Store").write_bytes(b"x")
        _, text = self.run_script()
        self.assertIn("Ничего не изменилось.", text)
        self.assertNotIn(".DS_Store", text)

    def test_subfolders_are_not_files(self):
        (self.folder / "Вложенная").mkdir()
        _, text = self.run_script()
        self.assertIn("Файлов в папке: 0.", text)

    def test_report_is_appended(self):
        self.run_script()
        self.run_script()
        _, text = self.run_script()
        self.assertEqual(text.count("папка «Входящие»"), 3)

    def test_missing_folder(self):
        code, text = self.run_script(self.folder.parent / "Нет такой папки")
        self.assertEqual(code, 3)
        self.assertIn("папка не найдена", text)
        self.assertNotIn("Файлов в папке", text)

    def test_missing_folder_does_not_lose_state(self):
        # Папку «потеряли» и вернули — скрипт не должен считать это первой проверкой.
        self.add("Пример.txt")
        self.run_script()
        self.folder.rename(self.folder.parent / "Временно")
        code, _ = self.run_script()
        self.assertEqual(code, 3)
        (self.folder.parent / "Временно").rename(self.folder)
        _, text = self.run_script()
        self.assertTrue(text.rstrip().endswith("Ничего не изменилось."))

    def test_broken_state_file(self):
        self.state.write_text("это не JSON", encoding="utf-8")
        code, text = self.run_script()
        self.assertEqual(code, 0)
        self.assertIn("Первая проверка", text)


if __name__ == "__main__":
    unittest.main()
