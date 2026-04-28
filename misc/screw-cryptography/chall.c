#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <sys/sendfile.h>

int main () {
	char guessme[0x20] = {0};
	char input[0x20] = {0};
	int flagfd = open("/home/priv/flag.txt", 0);
	int fd = open("/dev/urandom", 0);
	read(fd, guessme, 0x20);
	puts("your guess: ");
	int ret = read(0, input, 0x20);
	if (ret != 0x20) {
		puts("good idea, maybe for another chall");
		exit(1);
	}
	if (memcmp(guessme, input, 0x20) == 0) {
		sendfile(1, flagfd, 0, 0x100);
	} else {
		puts("next time inshaalah");
	}
	return 0;

}
