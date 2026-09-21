#include "parser.hpp"
#include <cstdlib>
#include <cctype>

std::string CommandParser::expandEnv(const std::string& input) {
    std::string result;
    for (size_t i = 0; i < input.size(); ++i) {
        if (input[i] == '$' && i + 1 < input.size()) {
            size_t start = ++i;
            while (i < input.size() && (std::isalnum(input[i]) || input[i] == '_')) {
                ++i;
            }
            std::string varName = input.substr(start, i - start);
            const char* val = std::getenv(varName.c_str());
            if (val) {
                result += val;
            }
            --i;
        } else {
            result += input[i];
        }
    }
    return result;
}

std::vector<std::string> CommandParser::tokenize(const std::string& line) {
    std::string expanded = expandEnv(line);
    std::vector<std::string> tokens;
    std::string current;
    bool inQuotes = false;
    bool inToken = false;

    for (char ch : expanded) {
        if (ch == '"') {
            inQuotes = !inQuotes;
            inToken = true;
        } else if (std::isspace(static_cast<unsigned char>(ch)) && !inQuotes) {
            if (inToken) {
                tokens.push_back(current);
                current.clear();
                inToken = false;
            }
        } else {
            current += ch;
            inToken = true;
        }
    }
    if (inToken) {
        tokens.push_back(current);
    }
    return tokens;
}
