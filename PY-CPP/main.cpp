#include <iostream>
#include <chrono>
#include <cstdint>
#include <algorithm>
#include <iomanip>

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    const int n = 10000;
    const uint32_t initial_seed = 42;
    const int min_val = -10;
    const int max_val = 10;
    const uint32_t range = max_val - min_val + 1;

    auto start_time = std::chrono::high_resolution_clock::now();

    long long total_sum = 0;
    uint32_t outer_seed = initial_seed;

    for (int run = 0; run < 20; ++run) {
        outer_seed = 1664525U * outer_seed + 1013904223U;
        uint32_t inner_seed = outer_seed;

        // Kadane's Algorithm to find Maximum Subarray Sum in O(N)
        inner_seed = 1664525U * inner_seed + 1013904223U;
        long long current_val = (int)(inner_seed % range) + min_val;
        long long max_sum = current_val;
        long long current_sum = current_val;

        for (int i = 1; i < n; ++i) {
            inner_seed = 1664525U * inner_seed + 1013904223U;
            long long val = (int)(inner_seed % range) + min_val;
            current_sum = std::max(val, current_sum + val);
            max_sum = std::max(max_sum, current_sum);
        }

        total_sum += max_sum;
    }

    auto end_time = std::chrono::high_resolution_clock::now();
    double duration = std::chrono::duration<double>(end_time - start_time).count();

    std::cout << "Total Maximum Subarray Sum (20 runs): " << total_sum << "\n";
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "Execution Time: " << duration << " seconds\n";

    return 0;
}