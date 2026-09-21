#include "shell.hpp"
#include <sstream>
#include <unistd.h>

static const int DEFAULT_HEAD_LIMIT = 10;

static std::string base64Decode(const std::string& in) {
    std::string out;
    std::vector<int> T(256, -1);
    for (int i = 0; i < 64; i++) {
        T["ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[i]] = i;
    }
    int val = 0, valb = -8;
    for (unsigned char c : in) {
        if (T[c] == -1) break;
        val = (val << 6) + T[c];
        valb += 6;
        if (valb >= 0) {
            out.push_back(char((val >> valb) & 0xFF));
            valb -= 8;
        }
    }
    return out;
}

ShellEmulator::ShellEmulator(VirtualFileSystem& vfs) : vfs_(vfs) {}

std::pair<std::string, bool> ShellEmulator::execute(
    const std::string& cmd, const std::vector<std::string>& args) {
    if (cmd == "exit") return {"", true};
    if (cmd == "ls") return {cmdLs(args), false};
    if (cmd == "cd") return {cmdCd(args), false};
    if (cmd == "head") return {cmdHead(args), false};
    if (cmd == "who") return {cmdWho(), false};
    if (cmd == "rm") return {cmdRm(args), false};
    return {"Ошибка: неизвестная команда '" + cmd + "'", false};
}

std::string ShellEmulator::cmdLs(const std::vector<std::string>& args) {
    std::string target = args.empty() ? "." : args[0];
    auto node = vfs_.resolvePath(target);
    if (!node) return "ls: невозможно получить доступ к '" + target + "': Нет файла";
    if (!node->isDirectory) return node->name;

    std::string result;
    for (const auto& [name, _] : node->children) {
        result += name + "\n";
    }
    return result;
}

std::string ShellEmulator::cmdCd(const std::vector<std::string>& args) {
    if (args.empty()) {
        vfs_.changeDirectory("/");
        return "";
    }
    if (!vfs_.changeDirectory(args[0])) {
        return "cd: " + args[0] + ": Нет такого файла или каталога";
    }
    return "";
}

std::string ShellEmulator::cmdHead(const std::vector<std::string>& args) {
    int maxLines = DEFAULT_HEAD_LIMIT;
    size_t fileIdx = 0;
    if (args.size() >= 2 && args[0] == "-n") {
        maxLines = std::stoi(args[1]);
        fileIdx = 2;
    }
    if (fileIdx >= args.size()) return "head: пропущен операнд файла";

    auto node = vfs_.resolvePath(args[fileIdx]);
    if (!node || node->isDirectory) return "head: " + args[fileIdx] + ": Ошибка открытия файла";

    std::string content = base64Decode(node->contentBase64);
    std::stringstream ss(content);
    std::string line, out;
    int count = 0;
    while (count < maxLines && std::getline(ss, line)) {
        out += line + "\n";
        count++;
    }
    return out;
}

std::string ShellEmulator::cmdWho() {
    char user[256];
    getlogin_r(user, sizeof(user));
    return std::string(user) + "     console";
}

std::string ShellEmulator::cmdRm(const std::vector<std::string>& args) {
    if (args.empty()) return "rm: пропущен операнд";
    if (!vfs_.removeFile(args[0])) {
        return "rm: невозможно удалить '" + args[0] + "': Нет файла или каталог";
    }
    return "";
}
