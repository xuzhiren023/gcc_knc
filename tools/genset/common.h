#ifndef GENSET_COMMON_H
#define GENSET_COMMON_H
#include <cstdio>
#include <cmath>
#include <ctime>
#include <cstdlib>
inline void value(double x) { std::printf("%.17g\n", x); }
struct kernel_clock {
    const char *name;
    clock_t start;
    kernel_clock(const char *n): name(n), start(clock()) {}
    ~kernel_clock() { std::fprintf(stderr, "GENSET_KERNEL %s seconds=%.9g\n", name,
                                  double(clock()-start)/CLOCKS_PER_SEC); }
};
inline bool close_value(double x, double y) {
    if (std::isnan(x) || std::isnan(y)) return std::isnan(x) && std::isnan(y);
    if (std::isinf(x) || std::isinf(y)) return x == y;
    return std::fabs(x-y) <= 1e-10 + 1e-8*std::fabs(y);
}
#endif
