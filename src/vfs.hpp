#pragma once
#include <map>
#include <memory>
#include <string>
#include <vector>

struct VFSNode {
    std::string name;
    bool isDirectory{false};
    std::string contentBase64;
    std::map<std::string, std::shared_ptr<VFSNode>> children;

    VFSNode(std::string n, bool isDir) : name(std::move(n)), isDirectory(isDir) {}
};

class VirtualFileSystem {
public:
    VirtualFileSystem();
    bool loadFromZip(const std::string& zipPath);
    std::shared_ptr<VFSNode> resolvePath(const std::string& path);
    bool changeDirectory(const std::string& path);
    bool removeFile(const std::string& path);
    const std::vector<std::string>& getCwd() const { return cwd_; }

private:
    std::shared_ptr<VFSNode> root_;
    std::vector<std::string> cwd_;
    void addEntry(const std::string& rawPath, const std::string& data);
};
