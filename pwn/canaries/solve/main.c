#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

enum
{
    CANARY_COUNT = 4
};

unsigned int g_pet_canary_state[CANARY_COUNT];

typedef struct CanaryStat
{
    const char *name;
    __uint64_t weight;
    const char *type;
} CanaryStat;

CanaryStat g_canary_stats[CANARY_COUNT] = {
    {"Cookie", 320, "Yellow Domestic"},
    {"Nugget", 290, "Green Singer"},
    {"Sunny", 340, "Orange Crested"},
    {"Echo", 305, "White Alpine"},
};

int banner(void)
{

    setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);

#define RESET "\x1b[0m"
#define YELLOW "\x1b[33m"
#define ORANGE "\x1b[38;5;208m"
#define WHITE "\x1b[97m"
#define GRAY "\x1b[90m"

    printf(
        GRAY "           .-\"\"\"-.\n" RESET GRAY "         .'  .-.  '.\n" RESET YELLOW "        /   /" WHITE "o o" YELLOW "\\   \\\n" RESET YELLOW "       |   |  " ORANGE "v" YELLOW "  |   |\n" RESET YELLOW "       |   | " WHITE "\\_/" YELLOW " |   |\n" RESET YELLOW "        \\   '---'   /\n" RESET YELLOW "         '._/___\\_.'\n" RESET ORANGE "            / | \\\n" RESET ORANGE "           /  |  \\\n" RESET ORANGE "          /___|___\\\n" RESET ORANGE "             / \\\n" RESET ORANGE "            /___\\\n" RESET);

    return 0;
}


void menu() {
    printf("welcome to the pet store, our favorite canary is retiring today\n");
    printf("0) name the canary\n");
    printf("1) print canaries\n");
    printf("2) print canary stats\n");
}
int main()
{


    char buf[16] = "Cookie";
    __uint16_t length = 16;

    while (1)
    {
        banner();
        menu();
        int option = 0;
        if (scanf("%d%*c", &option) != 1)
        {
            printf("Good Bye!\n");
            return 0;
        }

        switch (option)
        {
        case 0:
        {
            printf("what will his name be?\n");
            length = read(0, buf, length);
            buf[length - 1] = 0;
            length = length - 1;
            printf("size: %d\n", length);
            printf("'%s'\n", buf);
            break;
        }
        case 1:
        {
            for (int i = 0; i < CANARY_COUNT; ++i)
            {
                printf("[%d] %s\n", i, g_canary_stats[i].name);
            }
            break;
        }

        case 2:
        {
            int index = -1;
            printf("select canary index (0-%d):\n", CANARY_COUNT - 1);
            if (scanf("%d%*c", &index) != 1)
            {
                printf("invalid input\n");
                break;
            }
            if (index > CANARY_COUNT)
            {
                printf("index out of range\n");
                break;
            }

            const CanaryStat *canary = &g_canary_stats[index];
            printf("canary[%d]\n", index);
            printf("name: %s\n", canary->name);
            printf("weight: %u\n", canary->weight);
            printf("type: %s\n", canary->type);
            break;
        }

        default:
        {
            printf("unknown option\n");
            break;
        }
        }
    }

    return 0;
}
