#include "parser.hpp"
#include "shell.hpp"
#include "vfs.hpp"
#include <cassert>
#include <iostream>

void testParser() {
    auto tokens = CommandParser::tokenize("head -n 2 \"folder/file name.txt\"");
    assert(tokens.size() == 4);
    assert(tokens[0] == "head");
    assert(tokens[1] == "-n");
    assert(tokens[2] == "2");
    assert(tokens[3] == "folder/file name.txt");
    std::cout << "[PASS] CommandParser" << std::endl;
}

void testVFS() {
    VirtualFileSystem vfs;
    assert(vfs.loadFromZip("test_vfs.zip"));
    ShellEmulator shell(vfs);

    auto [resLs, _] = shell.execute("ls", {});
    assert(resLs.find("folder1") != std::string::npos);

    auto [resCd, __] = shell.execute("cd", {"folder1"});
    assert(resCd.empty());

    auto [resRm, ___] = shell.execute("rm", {"notes.txt"});
    assert(resRm.empty());

    auto [resLsAfter, ____] = shell.execute("ls", {});
    assert(resLsAfter.find("notes.txt") == std::string::npos);
    std::cout << "[PASS] VFS & Commands" << std::endl;
}

int main() {
    testParser();
    testVFS();
    std::cout << "Все тесты успешно пройдены!" << std::endl;
    return 0;
}
