// Winter AI -- C++ Fuzzy Scorer + Unreal Engine Remote-Control Bridge
// Real Levenshtein DP + structured UE Remote Control payload.
// Usage: ./engine <query> <candidate1> [candidate2 ...]
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>

static int levenshtein(const std::string& a, const std::string& b) {
    const size_t n = a.size(), m = b.size();
    std::vector<std::vector<int>> dp(n+1, std::vector<int>(m+1, 0));
    for (size_t i = 0; i <= n; ++i) dp[i][0] = (int)i;
    for (size_t j = 0; j <= m; ++j) dp[0][j] = (int)j;
    for (size_t i = 1; i <= n; ++i)
        for (size_t j = 1; j <= m; ++j) {
            int cost = (std::tolower(a[i-1]) == std::tolower(b[j-1])) ? 0 : 1;
            dp[i][j] = std::min({dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost});
        }
    return dp[n][m];
}

static std::string sanitize(const std::string& s) {
    std::string o; o.reserve(s.size());
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { o += '\\'; o += (char)c; }
        else if (c == '\n') o += ' ';
        else o += (char)c;
    }
    if (o.size() > 160) o = o.substr(0, 160);
    return o;
}

int main(int argc, char** argv) {
    std::cout << "ENGINE: C++ (native, compiled)\n";
    if (argc < 2) { std::cout << "STATUS: no_input\n"; return 0; }
    std::string query = argv[1];
    std::string best; int best_dist = -1;
    for (int i = 2; i < argc; ++i) {
        std::string c = argv[i];
        int d = levenshtein(query, c);
        if (best_dist == -1 || d < best_dist) { best_dist = d; best = c; }
    }
    std::cout << "BEST_MATCH: " << (best_dist >= 0 ? best : "none") << "\n";
    std::cout << "EDIT_DISTANCE: " << best_dist << "\n";
    std::cout << "UE_REMOTE_CONTROL_PAYLOAD: {\"ObjectPath\":\"/Game/WinterAI/BP_Assistant\","
              << "\"FunctionName\":\"ReceiveWinterAIReply\","
              << "\"Parameters\":{\"Text\":\"" << sanitize(query) << "\"}}\n";
    std::cout << "TRACE: dp[i][j]=min(dp[i-1][j]+1,dp[i][j-1]+1,dp[i-1][j-1]+cost)\n";
    return 0;
}
