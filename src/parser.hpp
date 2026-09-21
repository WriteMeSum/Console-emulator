#pragma once
#include <string>
#include <vector>

class CommandParser {
public:
    static std::string expandEnv(const std::string& input);
    static std::vector<std::string> tokenize(const std::string& line);
};
