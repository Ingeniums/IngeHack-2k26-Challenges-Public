#include <time.h>
#include <sys/types.h>

int clock_gettime(clockid_t clk_id, struct timespec *tp) {
    tp->tv_sec = 1776851984;
    tp->tv_nsec = 686049083;
    return 0;
}