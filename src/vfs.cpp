#include "vfs.hpp"
#include <fstream>
#include <sstream>

static const std::string BASE64_CHARS =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static std::string base64Encode(const std::string& in) {
    std::string out;
    int val = 0, valb = -6;
    for (unsigned char c : in) {
        val = (val << 8) + c;
        valb += 8;
        while (valb >= 0) {
            out.push_back(BASE64_CHARS[(val >> valb) & 0x3F]);
            valb -= 6;
        }
    }
    if (valb > -6) {
        out.push_back(BASE64_CHARS[((val << 8) >> (valb + 8)) & 0x3F]);
    }
    while (out.size() % 4) {
        out.push_back('=');
    }
    return out;
}

VirtualFileSystem::VirtualFileSystem() {
    root_ = std::make_shared<VFSNode>("", true);
}

void VirtualFileSystem::addEntry(const std::string& rawPath, const std::string& data) {
    std::stringstream ss(rawPath);
    std::string part;
    std::vector<std::string> parts;
    while (std::getline(ss, part, '/')) {
        if (!part.empty()) parts.push_back(part);
    }
    if (parts.empty()) return;

    auto curr = root_;
    for (size_t i = 0; i < parts.size() - 1; ++i) {
        if (curr->children.find(parts[i]) == curr->children.end()) {
            curr->children[parts[i]] = std::make_shared<VFSNode>(parts[i], true);
        }
        curr = curr->children[parts[i]];
    }

    bool isDir = (rawPath.back() == '/');
    auto leaf = std::make_shared<VFSNode>(parts.back(), isDir);
    if (!isDir) {
        leaf->contentBase64 = base64Encode(data);
    }
    curr->children[parts.back()] = leaf;
}

bool VirtualFileSystem::loadFromZip(const std::string& zipPath) {
    std::ifstream file(zipPath, std::ios::binary);
    if (!file.is_open()) return false;

    while (file) {
        uint32_t sig = 0;
        file.read(reinterpret_cast<char*>(&sig), sizeof(sig));
        if (sig != 0x04034b50) break;

        file.seekg(14, std::ios::cur);
        uint32_t compSize = 0, uncompSize = 0;
        uint16_t nameLen = 0, extraLen = 0;
        file.read(reinterpret_cast<char*>(&compSize), 4);
        file.read(reinterpret_cast<char*>(&uncompSize), 4);
        file.read(reinterpret_cast<char*>(&nameLen), 2);
        file.read(reinterpret_cast<char*>(&extraLen), 2);

        std::string filename(nameLen, '\0');
        file.read(&filename[0], nameLen);
        file.seekg(extraLen, std::ios::cur);

        std::string data(compSize, '\0');
        file.read(&data[0], compSize);
        addEntry(filename, data);
    }
    return true;
}

std::shared_ptr<VFSNode> VirtualFileSystem::resolvePath(const std::string& path) {
    std::vector<std::string> parts = (path.empty() || path[0] != '/') ? cwd_ : std::vector<std::string>();
    std::stringstream ss(path);
    std::string part;
    while (std::getline(ss, part, '/')) {
        if (part == "..") {
            if (!parts.empty()) parts.pop_back();
        } else if (!part.empty() && part != ".") {
            parts.push_back(part);
        }
    }
    auto curr = root_;
    for (const auto& p : parts) {
        if (curr->children.find(p) == curr->children.end()) return nullptr;
        curr = curr->children[p];
    }
    return curr;
}

bool VirtualFileSystem::changeDirectory(const std::string& path) {
    auto node = resolvePath(path);
    if (!node || !node->isDirectory) return false;

    if (path.empty() || path == ".") return true;
    if (path[0] == '/') cwd_.clear();

    std::stringstream ss(path);
    std::string part;
    while (std::getline(ss, part, '/')) {
        if (part == "..") {
            if (!cwd_.empty()) cwd_.pop_back();
        } else if (!part.empty() && part != ".") {
            cwd_.push_back(part);
        }
    }
    return true;
}

bool VirtualFileSystem::removeFile(const std::string& path) {
    auto node = resolvePath(path);
    if (!node || node->isDirectory) return false;

    std::vector<std::string> parts = (path.empty() || path[0] != '/') ? cwd_ : std::vector<std::string>();
    std::stringstream ss(path);
    std::string item;
    while (std::getline(ss, item, '/')) {
        if (!item.empty() && item != ".") parts.push_back(item);
    }

    std::string filename = parts.back();
    parts.pop_back();

    auto curr = root_;
    for (const auto& p : parts) {
        if (curr->children.find(p) == curr->children.end()) return false;
        curr = curr->children[p];
    }
    curr->children.erase(filename);
    return true;
}
