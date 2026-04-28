#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"
#include "kernel/fcntl.h"


char hex2byte(char a, char b) {
    int hi = (a <= '9') ? a - '0' : (a <= 'F') ? a - 'A' + 10 : a - 'a' + 10;
    int lo = (b <= '9') ? b - '0' : (b <= 'F') ? b - 'A' + 10 : b - 'a' + 10;
    return (hi << 4) | lo;
}

int
main(int argc, char **argv)
{
  if (argc != 3) {
    fprintf(2, "usage: <file> path size\n");
    exit(1);
  }
  char* path = argv[1];
  uint size = atoi(argv[2]);
  int fd = open(path, O_CREATE|O_RDWR);
  char buf[102];
  for (int i = 0; i < size; i+=50){
    int left = size-i > 50 ? 50 : size-i;
    printf("reading @%d %d bytes: ", i, left);
    read(0, buf, left*2 + 1);
    buf[left*2] = 0;
    for (int j = 0; j < left; j++) {
      int d = hex2byte(buf[j*2], buf[j*2+1]);
      write(fd, &d, 1);
    }
  }

  exit(0);
}
