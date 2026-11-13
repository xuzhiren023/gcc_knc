/* Unmodified re2c 3.1 generated example; only its example main is renamed. */
#define main upstream_lexer_main
#include "parse_etc_passwd.c"
#undef main
#include <time.h>
int main(void) {
    /* Static storage supplies YYMAXFILL trailing zero bytes on every record. */
    static const char records[][128]={
        "root:x:0:0:root:/root:/bin/bash\n",
        "bin:x:1:1::/bin:/bin/false\n",
        "portage:x:250:250:portage:/var/tmp/portage:/bin/false\n",
        "", "bad", ":x:1:1::/:/bin/sh\n",
        "user:x:no:1::/:/bin/sh\n", "u:x:1:1::/:/bin/sh",
        "u:x:1:1::/:/bin/sh\ntruncated\n"
    };
    static const int expected[]={0,0,0,0,1,1,1,1,1};
    size_t i;
    clock_t start=clock();
    puts("Q6 9");
    for(i=0;i<sizeof(expected)/sizeof(expected[0]);++i) {
        int result=lex(records[i]);
        if(result!=expected[i]) return 1;
        printf("%lu %d\n",(unsigned long)i,result);
    }
    fprintf(stderr,"GENSET_KERNEL Q6-lexer seconds=%.9g\n",(double)(clock()-start)/CLOCKS_PER_SEC);
    return ferror(stdout) || ferror(stderr) ? 2 : 0;
}
