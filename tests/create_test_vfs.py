import zipfile


def make_vfs(path="test_vfs.zip"):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("root.txt", "Первая строка\nВторая строка\nТретья строка\n")
        zf.writestr("folder1/notes.txt", "Заметка 1\nЗаметка 2\nЗаметка 3\n")
        zf.writestr("folder1/sub/deep.txt", "Вложенный файл\n")


if __name__ == "__main__":
    make_vfs()
