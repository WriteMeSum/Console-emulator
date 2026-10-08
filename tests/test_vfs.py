"""модуль тестов для проверки логики VFS эмулятора."""

import unittest
import zipfile
import os
from pathlib import PurePosixPath
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from src.emulator import VirtualFileSystem


class TestVirtualFileSystem(unittest.TestCase):
    """тесты для проверки команд внутри VFS."""

    def set_up(self):
        """создание временного ZIP-архива перед каждым тестом."""
        self.test_zip = "temp_test_vfs.zip"
        with zipfile.ZipFile(self.test_zip, "w") as z:
            z.writestr("docs/", "")
            z.writestr("docs/test.txt", "Line 1\nLine 2\n")
            z.writestr("notes.txt", "Hello notes\n")
        self.vfs = VirtualFileSystem(self.test_zip)

    def tear_down(self):
        """Удаление временного архива после теста."""
        if os.path.exists(self.test_zip):
            os.remove(self.test_zip)

    def test_list_dir_root(self):
        """проверка команды ls в корневом каталоге."""
        self.set_up()
        items = self.vfs.list_dir(PurePosixPath("/"))
        self.assertIn("docs/", items)
        self.assertIn("notes.txt", items)
        self.tear_down()

    def test_change_dir_valid(self):
        """проверка успешной смены каталога (cd docs)."""
        self.set_up()
        success, _ = self.vfs.change_dir("docs")
        self.assertTrue(success)
        self.assertEqual(self.vfs.cwd, PurePosixPath("/docs"))
        self.tear_down()

    def test_change_dir_invalid(self):
        """проверка ошибки при переходе в несуществующий каталог."""
        self.set_up()
        success, err = self.vfs.change_dir("invalid_folder")
        self.assertFalse(success)
        self.assertIn("Каталог не найден", err)
        self.tear_down()

    def test_read_file_valid(self):
        """проверка чтения существующего файла (head)."""
        self.set_up()
        success, content = self.vfs.read_file("notes.txt")
        self.assertTrue(success)
        self.assertEqual(content.decode("utf-8"), "Hello notes\n")
        self.tear_down()

    def test_remove_file(self):
        """проверка логики удаления файла (rm)."""
        self.set_up()
        success, _ = self.vfs.remove_file("notes.txt")
        self.assertTrue(success)
        self.assertFalse(self.vfs.is_file(PurePosixPath("/notes.txt")))
        self.tear_down()


if __name__ == "__main__":
    unittest.main()