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
    """виртуальная файловая система, хранящаяся в оперативной памяти."""

    def __init__(self, zip_path=None):
        self.files = {}
        self.dirs = {PurePosixPath("/")}
        self.cwd = PurePosixPath("/")

        if zip_path:
            if not os.path.exists(zip_path):
                print(f"Критическая ошибка: файл VFS '{zip_path}' не найден.")
                sys.exit(1)
            try:
                self.load_from_zip(zip_path)
            except zipfile.BadZipFile:
                print(f"Критическая ошибка: '{zip_path}' не является корректным ZIP-архивом.")
                sys.exit(1)

    def load_from_zip(self, zip_path):
        """загрузка файлов и каталогов из ZIP-архива в память."""
        with zipfile.ZipFile(zip_path, "r") as archive:
            for info in archive.infolist():
                raw_path = "/" + info.filename.lstrip("/")
                norm_path = PurePosixPath(raw_path)

                if info.is_dir():
                    self._add_dir_recursive(norm_path)
                else:
                    self._add_dir_recursive(norm_path.parent)
                    self.files[norm_path] = archive.read(info.filename)

    def _add_dir_recursive(self, path):
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
        return path in self.dirs

    def is_file(self, path):
        return path in self.files

    def list_dir(self, path):
        """возвращает список имен объектов в каталоге path."""
        entries = set()
        for d in self.dirs:
            if d != path and d.parent == path:
                entries.add(d.name + "/")

        for f in self.files:
            if f.parent == path:
                entries.add(f.name)

        return sorted(list(entries))

    def change_dir(self, path_str):
        target = self.resolve_path(path_str)
        if self.is_dir(target):
            self.cwd = target
            return True, ""
        elif self.is_file(target):
            return False, f"cd: {path_str}: Не является директорией"
        else:
            return False, f"cd: {path_str}: Каталог не найден"

    def read_file(self, path_str):
        target = self.resolve_path(path_str)
        if self.is_file(target):
            return True, self.files[target]
        elif self.is_dir(target):
            return False, f"head: {path_str}: Является директорией"
        else:
            return False, f"head: {path_str}: Файл не найден"

    def remove_file(self, path_str):
        target = self.resolve_path(path_str)
        if self.is_file(target):
            del self.files[target]
            return True, ""
        elif self.is_dir(target):
            return False, f"rm: невозможно удалить '{path_str}': Это каталог"
        else:
            return False, f"rm: невозможно удалить '{path_str}': Файл не найден"


class EmulatorGUI:
    """граф терминал на базе Tkinter."""

    def __init__(self, root, vfs, username, script_path=None):
        self.root = root
        self.vfs = vfs
        self.username = username
        self.script_path = script_path

        hostname = socket.gethostname()
        self.root.title(f"Эмулятор - [{self.username}@{hostname}]")
        self.root.geometry("820x520")
        self.root.configure(bg="#1e1e1e")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.terminal = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#cccccc",
            insertbackground="#00ff66",
            font=("Courier", 14),
            padx=10,
            pady=10,
            state=tk.DISABLED,
            highlightthickness=0,
            borderwidth=0
        )
        self.terminal.grid(row=0, column=0, sticky="nsew")

        self.terminal.tag_config("prompt", foreground="#5af78e")
        self.terminal.tag_config("error", foreground="#ff5c57")
        self.terminal.tag_config("output", foreground="#e6e6e6")
        self.terminal.tag_config("command", foreground="#57c7ff")

        self.bottom_frame = tk.Frame(self.root, bg="#181818")
        self.bottom_frame.grid(row=1, column=0, sticky="ew")

        self.prompt_label = tk.Label(
            self.bottom_frame,
            text="",
            bg="#181818",
            fg="#5af78e",
            font=("Courier", 14, "bold")
        )
        self.prompt_label.pack(side=tk.LEFT, padx=(10, 0), pady=6)

        self.entry = tk.Entry(
            self.bottom_frame,
            bg="#181818",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Courier", 14),
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 10), pady=6)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.focus_set()

        self.update_prompt()
        self.print_text("Эмулятор терминала запущен. Добро пожаловать!\n", "output")
        self.run_startup_script()

    def get_prompt_str(self):
        return f"{self.username}@vfs:{self.vfs.cwd}$ "

    def update_prompt(self):
        self.prompt_label.config(text=self.get_prompt_str())

    def print_text(self, text, tag="output"):
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, text, tag)
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)

    def on_enter(self, event=None):
        cmd_line = self.entry.get()
        self.entry.delete(0, tk.END)
        self.execute_command(cmd_line)

    def execute_command(self, cmd_line):
        cmd_line = os.path.expandvars(cmd_line)
        self.print_text(self.get_prompt_str(), "prompt")
        self.print_text(f"{cmd_line}\n", "command")

        line = cmd_line.strip()
        if not line:
            return

        parts = line.split()
        cmd = parts[0]
        args = parts[1:]

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

        self.update_prompt()

    def cmd_ls(self, args):
        target = self.vfs.cwd if not args else self.vfs.resolve_path(args[0])
        if not self.vfs.is_dir(target):
            self.print_text(f"ls: невозможно получить доступ к '{args[0]}': Нет такого каталога\n", "error")
            return
        items = self.vfs.list_dir(target)
        if items:
            self.print_text("  ".join(items) + "\n", "output")

    def cmd_cd(self, args):
        path = args[0] if args else "/"
        success, err = self.vfs.change_dir(path)
        if not success:
            self.print_text(err + "\n", "error")

    def cmd_head(self, args):
        lines_count = 10
        filename = None

        idx = 0
        while idx < len(args):
            if args[idx] == "-n":
                if idx + 1 < len(args):
                    try:
                        lines_count = int(args[idx + 1])
                        idx += 2
                        continue
                    except ValueError:
                        self.print_text(f"head: неверное количество строк: '{args[idx + 1]}'\n", "error")
                        return
                else:
                    self.print_text("head: опция требует аргумент -- 'n'\n", "error")
                    return
            else:
                filename = args[idx]
                idx += 1

        if not filename:
            self.print_text("head: пропущен операнд, задающий файл\n", "error")
            return

        success, content = self.vfs.read_file(filename)
        if not success:
            self.print_text(content + "\n", "error")
            return

        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines()[:lines_count]
        self.print_text("\n".join(lines) + ("\n" if lines else ""), "output")

    def cmd_who(self, args):
        self.print_text(f"{self.username}  tty1  pts/0\n", "output")

    def cmd_rm(self, args):
        if not args:
            self.print_text("rm: пропущен операнд\n", "error")
            return
        success, err = self.vfs.remove_file(args[0])
        if not success:
            self.print_text(err + "\n", "error")

    def run_startup_script(self):
        """автоматическое выполнение стартового командного файла."""
        if not self.script_path:
            return

        if not os.path.exists(self.script_path):
            self.print_text(f"Стартовый скрипт '{self.script_path}' не найден.\n", "error")
            return

        self.print_text(f"--- Выполнение скрипта: {self.script_path} ---\n", "prompt")
        with open(self.script_path, "r", encoding="utf-8") as f:
            for line in f:
                cmd_line = line.strip()
                if cmd_line and not cmd_line.startswith("#"):
                    self.execute_command(cmd_line)
        self.print_text("--- Скрипт завершен ---\n\n", "prompt")


def main():
    parser = argparse.ArgumentParser(description="Эмулятор командной строки (Вариант №18)")
    parser.add_argument("--vfs", type=str, default="vfs.zip", help="Путь к ZIP-архиву виртуальной файловой системы")
    parser.add_argument("--script", type=str, default=None, help="Путь к стартовому командному файлу")
    args = parser.parse_args()

    vfs = VirtualFileSystem(args.vfs)
    current_user = getpass.getuser()

    root = tk.Tk()
    app = EmulatorGUI(root, vfs, current_user, args.script)
    root.update_idletasks()
    root.mainloop()


if __name__ == "__main__":
    main()