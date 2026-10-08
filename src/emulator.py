import sys
import os
import getpass
import argparse
import zipfile
import tkinter as tk
from tkinter import scrolledtext
from pathlib import PurePosixPath
import socket

class VirtualFileSystem:
    """виртуальная файловая система в оперативной памяти."""

    def __init__(self, zip_path=None):
        """инициализация VFS."""
        self.files = {}
        self.dirs = {PurePosixPath("/")}
        self.cwd = PurePosixPath("/")

        if zip_path:
            if not os.path.exists(zip_path):
                msg = f"Крит. ошибка: VFS '{zip_path}' не найден."
                print(msg)
                sys.exit(1)
            try:
                self.load_from_zip(zip_path)
            except zipfile.BadZipFile:
                msg = f"Крит. ошибка: '{zip_path}' не ZIP-архив."
                print(msg)
                sys.exit(1)

    def load_from_zip(self, zip_path):
        """загрузка файлов из ZIP-архива в память."""
        with zipfile.ZipFile(zip_path, "r") as archive:
            for info in archive.infolist():
                raw_path = "/" + info.filename.lstrip("/")
                norm_path = PurePosixPath(raw_path)

                if info.is_dir():
                    self._add_dir_recursive(norm_path)
                else:
                    self._add_dir_recursive(norm_path.parent)
                    data = archive.read(info.filename)
                    self.files[norm_path] = data

    def _add_dir_recursive(self, path):
        """рекурсивное добавление родительских директорий."""
        curr = path
        while curr != PurePosixPath("/"):
            self.dirs.add(curr)
            curr = curr.parent
        self.dirs.add(PurePosixPath("/"))

    def resolve_path(self, path_str):
        """разрешение относительного пути относительно cwd."""
        import posixpath
        target = PurePosixPath(path_str)
        if target.is_absolute():
            resolved = posixpath.normpath(str(target))
        else:
            resolved = posixpath.normpath(str(self.cwd / target))
        return PurePosixPath(resolved)

    def is_dir(self, path):
        """апроверка, является ли путь директорией."""
        return path in self.dirs

    def is_file(self, path):
        """проверка, является ли путь файлом."""
        return path in self.files

    def list_dir(self, path):
        """возвращает список объектов в каталоге."""
        entries = set()
        for d in self.dirs:
            if d != path and d.parent == path:
                entries.add(d.name + "/")

        for f in self.files:
            if f.parent == path:
                entries.add(f.name)

        return sorted(list(entries))

    def change_dir(self, path_str):
        """смена директории."""
        target = self.resolve_path(path_str)
        if self.is_dir(target):
            self.cwd = target
            return True, ""
        elif self.is_file(target):
            return False, f"cd: {path_str}: Не является директорией"
        else:
            return False, f"cd: {path_str}: Каталог не найден"

    def read_file(self, path_str):
        """чтение файла."""
        target = self.resolve_path(path_str)
        if self.is_file(target):
            return True, self.files[target]
        elif self.is_dir(target):
            return False, f"head: {path_str}: Является директорией"
        else:
            return False, f"head: {path_str}: Файл не найден"

    def remove_file(self, path_str):
        """удаление файла."""
        target = self.resolve_path(path_str)
        if self.is_file(target):
            del self.files[target]
            return True, ""
        elif self.is_dir(target):
            err = f"rm: нельзя удалить '{path_str}': Это каталог"
            return False, err
        else:
            err = f"rm: нельзя удалить '{path_str}': Файл не найден"
            return False, err

class EmulatorGUI:
    """граф терминал на базе Tkinter."""

    def __init__(self, root, vfs, username, script_path=None):
        """инициализация интерфейса."""
        self.root = root
        self.vfs = vfs
        self.username = username
        self.script_path = script_path

        self._setup_window()
        self._setup_widgets()

        self.update_prompt()
        self.print_text("Эмулятор запущен. Добро пожаловать!\n")
        self.run_startup_script()

    def _setup_window(self):
        """настройка параметров главного окна."""
        hostname = socket.gethostname()
        self.root.title(f"Эмулятор - [{self.username}@{hostname}]")
        self.root.geometry("820x520")
        self.root.configure(bg="#1e1e1e")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def _setup_widgets(self):
        """создание и размещение виджетов."""
        self.terminal = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, bg="#1e1e1e", fg="#cccccc",
            insertbackground="#00ff66", font=("Courier", 14),
            padx=10, pady=10, state=tk.DISABLED,
            highlightthickness=0, borderwidth=0
        )
        self.terminal.grid(row=0, column=0, sticky="nsew")

        self.terminal.tag_config("prompt", foreground="#5af78e")
        self.terminal.tag_config("error", foreground="#ff5c57")
        self.terminal.tag_config("output", foreground="#e6e6e6")
        self.terminal.tag_config("command", foreground="#57c7ff")

        self.bottom_frame = tk.Frame(self.root, bg="#181818")
        self.bottom_frame.grid(row=1, column=0, sticky="ew")

        self.prompt_label = tk.Label(
            self.bottom_frame, text="", bg="#181818", fg="#5af78e",
            font=("Courier", 14, "bold")
        )
        self.prompt_label.pack(side=tk.LEFT, padx=(10, 0), pady=6)

        self.entry = tk.Entry(
            self.bottom_frame, bg="#181818", fg="#ffffff",
            insertbackground="#ffffff", font=("Courier", 14),
            relief=tk.FLAT, highlightthickness=0
        )
        self.entry.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 10), pady=6
        )
        self.entry.bind("<Return>", self.on_enter)
        self.entry.focus_set()

    def get_prompt_str(self):
        """формирование строки приглашения."""
        return f"{self.username}@vfs:{self.vfs.cwd}$ "

    def update_prompt(self):
        """обновление метки приглашения."""
        self.prompt_label.config(text=self.get_prompt_str())

    def print_text(self, text, tag="output"):
        """вывод текста в терминал."""
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, text, tag)
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)

    def on_enter(self, event=None):
        """обработка нажатия Enter."""
        cmd_line = self.entry.get()
        self.entry.delete(0, tk.END)
        self.execute_command(cmd_line)

    def execute_command(self, cmd_line):
        """разбор и выполнение команды."""
        cmd_line = os.path.expandvars(cmd_line)
        self.print_text(self.get_prompt_str(), "prompt")
        self.print_text(f"{cmd_line}\n", "command")

        line = cmd_line.strip()
        if not line:
            return

        parts = line.split()
        cmd = parts[0]
        args = parts[1:]

        self._dispatch_command(cmd, args)
        self.update_prompt()

    def _dispatch_command(self, cmd, args):
        """диспетчер команд."""
        if cmd == "ls":
            self.cmd_ls(args)
        elif cmd == "cd":
            self.cmd_cd(args)
        elif cmd == "head":
            self.cmd_head(args)
        elif cmd == "who":
            self.cmd_who(args)
        elif cmd == "rm":
            self.cmd_rm(args)
        elif cmd == "exit":
            self.root.destroy()
            sys.exit(0)
        else:
            self.print_text(f"Команда не найдена: {cmd}\n", "error")

    def cmd_ls(self, args):
        """команда ls."""
        target = self.vfs.cwd
        if args:
            target = self.vfs.resolve_path(args[0])

        if not self.vfs.is_dir(target):
            err = f"ls: нет доступа к '{args[0]}': Нет каталога\n"
            self.print_text(err, "error")
            return

        items = self.vfs.list_dir(target)
        if items:
            self.print_text("  ".join(items) + "\n", "output")

    def cmd_cd(self, args):
        """команда cd."""
        path = args[0] if args else "/"
        success, err = self.vfs.change_dir(path)
        if not success:
            self.print_text(err + "\n", "error")

    def cmd_head(self, args):
        """команда head."""
        count = 10
        fname = None
        i = 0
        while i < len(args):
            if args[i] == "-n":
                if i + 1 < len(args):
                    try:
                        count = int(args[i + 1])
                        i += 2
                        continue
                    except ValueError:
                        err = f"head: неверное число: '{args[i+1]}'\n"
                        self.print_text(err, "error")
                        return
                else:
                    err = "head: опция требует аргумент -- 'n'\n"
                    self.print_text(err, "error")
                    return
            else:
                fname = args[i]
                i += 1

        if not fname:
            self.print_text("head: пропущен операнд\n", "error")
            return

        success, content = self.vfs.read_file(fname)
        if not success:
            self.print_text(content + "\n", "error")
            return

        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines()[:count]
        self.print_text("\n".join(lines) + ("\n" if lines else ""))

    def cmd_who(self, args):
        """команда who."""
        self.print_text(f"{self.username}  tty1  pts/0\n", "output")

    def cmd_rm(self, args):
        """команда rm."""
        if not args:
            self.print_text("rm: пропущен операнд\n", "error")
            return
        success, err = self.vfs.remove_file(args[0])
        if not success:
            self.print_text(err + "\n", "error")

    def run_startup_script(self):
        """выполнение стартового скрипта."""
        if not self.script_path:
            return
        if not os.path.exists(self.script_path):
            err = f"Скрипт '{self.script_path}' не найден.\n"
            self.print_text(err, "error")
            return

        msg = f"--- Скрипт: {self.script_path} ---\n"
        self.print_text(msg, "prompt")
        with open(self.script_path, "r", encoding="utf-8") as f:
            for line in f:
                cmd = line.strip()
                if cmd and not cmd.startswith("#"):
                    self.execute_command(cmd)
        self.print_text("--- Скрипт завершен ---\n\n", "prompt")


def main():
    """точка входа."""
    desc = "Эмулятор командной строки (Вариант 18)"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--vfs", type=str, default="vfs.zip",
        help="Путь к архиву виртуальной файловой системы"
    )
    parser.add_argument(
        "--script", type=str, default=None,
        help="Путь к стартовому командному файлу"
    )
    args = parser.parse_args()

    vfs = VirtualFileSystem(args.vfs)
    root = tk.Tk()
    app = EmulatorGUI(root, vfs, getpass.getuser(), args.script)
    root.update_idletasks()
    root.mainloop()

if __name__ == "__main__":
    main()