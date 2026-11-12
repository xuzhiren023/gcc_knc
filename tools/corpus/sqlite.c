/* SQL is a staged frozen input; check its result with an independent loop. */
#include <stdio.h>
#include <stdlib.h>
#include <sqlite3.h>

static long long expected[3];
static int rows, correct;
static int check(void *unused, int columns, char **values, char **names)
{
  int i;
  (void)unused; (void)names;
  ++rows;
  if (columns != 3) return 1;
  for (i = 0; i < 3; ++i)
    if (!values[i] || atoll(values[i]) != expected[i]) return 1;
  correct = 1;
  return 0;
}

int main(void)
{
  char sql[8192], *error = 0;
  size_t length;
  int i, status;
  sqlite3 *db;
  FILE *f = fopen("input.sql", "rb");
  if (!f) return 2;
  length = fread(sql, 1, sizeof sql - 1, f);
  if (ferror(f) || !feof(f)) return 2;
  fclose(f);
  sql[length] = 0;
  for (i = 1; i <= 100000; ++i) if (i % 13) {
    ++expected[0];
    expected[1] += i;
    expected[2] += (i * 17 + 11) % 1009 + (i % 7 == 0 ? 3 : 0);
  }
  if (sqlite3_open(":memory:", &db) != SQLITE_OK) return 2;
  status = sqlite3_exec(db, sql, check, 0, &error);
  if (error) fprintf(stderr, "%s\n", error);
  sqlite3_free(error);
  sqlite3_close(db);
  if (status != SQLITE_OK || rows != 1 || !correct) return 1;
  puts("CORPUS_CHECK pass");
  return 0;
}
