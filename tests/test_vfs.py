"""модуль тестов для проверки логики VFS эмулятора."""

import unittest
import zipfile
import os
from pathlib import PurePosixPath
import sys

#добавляем родительскую директорию в путь, чтобы импортировать emulator.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from emulator import VirtualFileSystem

class TestVirtualFileSystem(unittest.TestCase):
    """тесты для проверки команд внутри VFS."""

    def setUp(self):
        """создание временного ZIP-архива перед каждым тестом."""
        self.test_zip = "temp_test_vfs.zip"
        with zipfile.ZipFile(self.test_zip, 'w') as z:
            z.writestr('docs/', '')
            z.writestr('docs/test.txt', 'Line 1\nLine 2\n')
            z.writestr('notes.txt', 'Hello notes\n')
        self.vfs = VirtualFileSystem(self.test_zip)

    def tearDown(self):
        """удаление временного архива после теста."""
        if os.path.exists(self.test_zip):
            os.remove(self.test_zip)

    def test_list_dir_root(self):
        """проверка команды ls в корневом каталоге."""
        items = self.vfs.list_dir(PurePosixPath("/"))
        self.assertIn("docs/", items)
        self.assertIn("notes.txt", items)

    def test_change_dir_valid(self):
        """проверка успешной смены каталога (cd docs)."""
        success, err = self.vfs.change_dir("docs")
        self.assertTrue(success)
        self.assertEqual(self.vfs.cwd, PurePosixPath("/docs"))

    def test_change_dir_invalid(self):
        """проверка ошибки при переходе в несуществующий каталог."""
        success, err = self.vfs.change_dir("invalid_folder")
        self.assertFalse(success)
        self.assertIn("Каталог не найден", err)

    def test_read_file_valid(self):
        """проверка чтения существующего файла (head)."""
        success, content = self.vfs.read_file("notes.txt")
        self.assertTrue(success)
        self.assertEqual(content.decode("utf-8"), "Hello notes\n")

    def test_remove_file(self):
        """проверка логики удаления файла (rm)."""
        success, _ = self.vfs.remove_file("notes.txt")
        self.assertTrue(success)
        self.assertFalse(self.vfs.is_file(PurePosixPath("/notes.txt")))

if __name__ == "__main__":
    unittest.main()