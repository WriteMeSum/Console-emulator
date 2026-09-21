#pragma once
#include "vfs.hpp"
#include <string>
#include <vector>

class ShellEmulator {
public:
    explicit ShellEmulator(VirtualFileSystem& vfs);
    std::pair<std::string, bool> execute(const std::string& cmd, const std::vector<std::string>& args);

private:
    VirtualFileSystem& vfs_;
    std::string cmdLs(const std::vector<std::string>& args);
    std::string cmdCd(const std::vector<std::string>& args);
    std::string cmdHead(const std::vector<std::string>& args);
    std::string cmdWho();
    std::string cmdRm(const std::vector<std::string>& args);
};
