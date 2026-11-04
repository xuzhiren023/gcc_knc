/* S4-12: unpack one tools/card_run stage stream into the current directory.
   card_run runs it as root from the guarded job directory, so it writes only
   plain names there, never follows or replaces an existing entry, and removes
   everything it created when the stream is short or malformed.

   usage: claude-unpack LENGTH < stream   (LENGTH is the exact stream size)
   stream: "claude-pack 1\n"
           then per file "<600|700> <size> <name>\n" and exactly <size> bytes
           then "end <count>\n" and end of input.
   Mode 700 is required for ELF data and 600 for everything else. Names follow
   card_run's staging_name: not empty, ".", "..", and no '/', '\\' or NUL.
   Build statically with the donor, like claude-pin (docs/card-run.md). */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define MAX_FILES 16384
#define MAX_LINE 512

static char *created[MAX_FILES];
static int created_count;
static unsigned char buffer[65536];
static size_t buffered, position;
static unsigned long long taken, total;

static int fail(const char *what, const char *name) {
    fprintf(stderr, "claude-unpack: %s%s%s\n", what, name ? ": " : "", name ? name : "");
    while (created_count > 0)
        unlink(created[--created_count]);
    return 1;
}

/* Make at least one unread byte available; 0 at end of input. */
static int refill(void) {
    ssize_t got;
    if (position < buffered) return 1;
    do got = read(0, buffer, sizeof buffer);
    while (got < 0 && errno == EINTR);
    if (got <= 0) return 0;
    buffered = (size_t)got;
    position = 0;
    return 1;
}

/* Next input byte, or -1 at end of input or at the declared length. */
static int next_byte(void) {
    if (taken == total || !refill()) return -1;
    ++taken;
    return buffer[position++];
}

/* One header line without its newline; NUL bytes and overlong lines fail. */
static int read_line(char *line) {
    size_t length = 0;
    int c;
    while ((c = next_byte()) != '\n') {
        if (c <= 0 || length + 1 >= MAX_LINE) return 0;
        line[length++] = (char)c;
    }
    line[length] = '\0';
    return 1;
}

/* Canonical decimal: digits only, no sign and no leading zero. */
static int parse_size(const char *text, const char **end, unsigned long long *value) {
    const char *p = text;
    *value = 0;
    if (*p < '0' || *p > '9' || (*p == '0' && p[1] >= '0' && p[1] <= '9')) return 0;
    for (; *p >= '0' && *p <= '9'; ++p) {
        if (*value > (~0ULL - 9) / 10) return 0;
        *value = *value * 10 + (unsigned)(*p - '0');
    }
    *end = p;
    return 1;
}

static int safe_name(const char *name) {
    static const char *const reserved[] = {"claude-unpack", "claude-pinned", "stdout", "stderr", "status"};
    size_t i;
    if (!*name || !strcmp(name, ".") || !strcmp(name, "..") || strpbrk(name, "/\\")) return 0;
    for (i = 0; i < sizeof reserved / sizeof *reserved; ++i)
        if (!strcmp(name, reserved[i])) return 0;
    return 1;
}

static int write_all(int fd, const unsigned char *data, size_t size) {
    ssize_t done;
    while (size) {
        done = write(fd, data, size);
        if (done < 0 && errno == EINTR) continue;
        if (done <= 0) return 0;
        data += done;
        size -= (size_t)done;
    }
    return 1;
}

/* Copy SIZE bytes into FD, remembering the first four for the ELF check. */
static int copy_body(int fd, unsigned long long size, unsigned char *head) {
    size_t chunk, i, seen = 0;
    while (size) {
        if (taken == total || !refill()) return 0;
        chunk = buffered - position;
        if (chunk > size) chunk = (size_t)size;
        if (chunk > total - taken) chunk = (size_t)(total - taken);
        for (i = 0; seen < 4 && i < chunk; ++i) head[seen++] = buffer[position + i];
        if (!write_all(fd, buffer + position, chunk)) return 0;
        position += chunk;
        taken += chunk;
        size -= chunk;
    }
    return 1;
}

int main(int argc, char **argv) {
    char line[MAX_LINE], *name;
    const char *end;
    unsigned long long size, count;
    unsigned char head[4];
    int fd, executable;
    mode_t mode;
    if (argc != 2 || !parse_size(argv[1], &end, &total) || *end)
        return fail("expected the exact stream length", NULL);
    if (!read_line(line) || strcmp(line, "claude-pack 1"))
        return fail("missing pack header", NULL);
    for (;;) {
        if (!read_line(line)) return fail("short or malformed entry header", NULL);
        if (!strncmp(line, "end ", 4)) {
            if (!parse_size(line + 4, &end, &count) || *end || count != (unsigned long long)created_count)
                return fail("file count mismatch", NULL);
            if (taken != total || refill())
                return fail("stream length mismatch", NULL);
            return 0;
        }
        if (strncmp(line, "600 ", 4) && strncmp(line, "700 ", 4))
            return fail("mode must be 600 or 700", NULL);
        mode = line[0] == '7' ? 0700 : 0600;
        if (!parse_size(line + 4, &end, &size) || *end != ' ' || size > total - taken)
            return fail("invalid file size", NULL);
        name = (char *)end + 1;
        if (!safe_name(name)) return fail("unsafe staging filename", name);
        if (created_count == MAX_FILES) return fail("too many files", NULL);
        /* O_EXCL refuses duplicates and existing entries; O_NOFOLLOW symlinks. */
        fd = open(name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
        if (fd < 0) return fail("cannot create", name);
        if ((created[created_count] = strdup(name)) == NULL) {
            close(fd);
            unlink(name);
            return fail("out of memory", NULL);
        }
        ++created_count;
        memset(head, 0, sizeof head);
        if (!copy_body(fd, size, head)) {
            close(fd);
            return fail("short stream or write failure", name);
        }
        executable = size >= 4 && !memcmp(head, "\177ELF", 4);
        if (mode != (executable ? 0700 : 0600)) {
            close(fd);
            return fail("mode does not match ELF content", name);
        }
        if (fchmod(fd, mode) != 0 || close(fd) != 0)
            return fail("cannot finish", name);
    }
}
