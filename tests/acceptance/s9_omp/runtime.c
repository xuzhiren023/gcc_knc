/* S9-06: exactly one OpenMP runtime is mapped, it is libgomp from the program's own directory (the
   staged copy, as RPATH $ORIGIN/../lib would pick in the prefix), and no libiomp5 is loaded.  */
#include "check.h"
#include <string.h>

int main (void)
{
  char line[4096], self[4096] = "", gomp_path[4096] = "";
  int gomp_paths = 0, iomp = 0;
  int nt = team_size ();
  FILE *maps = fopen ("/proc/self/maps", "r");
  while (maps && fgets (line, sizeof line, maps))
    {
      char *path = strchr (line, '/');
      if (!path)
        continue;
      path[strcspn (path, "\n")] = 0;
      if (strstr (path, "libiomp"))
        iomp++;
      if (strstr (path, "libgomp") && strcmp (path, gomp_path) != 0)
        {
          printf ("mapped %s\n", path);
          strcpy (gomp_path, path);
          gomp_paths++;
        }
      if (!self[0] && strstr (path, ".mic"))
        strcpy (self, path);
    }
  if (maps)
    fclose (maps);
  char *slash = strrchr (self, '/');
  size_t dirlen = slash ? (size_t) (slash - self) + 1 : 0;
  CHECK (gomp_paths == 1);
  CHECK (iomp == 0);
  CHECK (dirlen > 0 && strncmp (gomp_path, self, dirlen) == 0);
  return report ("runtime", nt);
}
