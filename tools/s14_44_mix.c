/* Original S14-44 integer/hash plus FP-score diagnostic, not zlib/bzip2 code.
   Fixed work: consume n bytes in order; preserve unsigned hash and FP sum. */
unsigned s14_mix(const unsigned char *data, const double *weights,
                 double *score, unsigned n)
{
  unsigned hash = 0;
  double sum = 0;
  for (unsigned i = 0; i < n; ++i) {
    hash = (hash << 5) ^ (hash >> 27) ^ data[i];
    sum += weights[data[i]];
  }
  *score = sum;
  return hash;
}
