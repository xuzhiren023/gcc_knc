// S9-05: documents from_chars(_Float128) on KNC (docs/research/knc-libstdcxx.md 1.7).
// Without _GLIBCXX_HAVE_FLOAT128_MATH (glibc 2.26) <charconv> does not declare it, but libstdc++
// exports it; it binds strtof128 weak and, when glibc lacks it, parses through strtold:
// 64-bit mantissa precision for a 113-bit type. 1 + 2^-100 tells the two apart.
#include <charconv>
#include <cstdio>
#include <cstring>

namespace std {
// The exported _ZSt10from_charsPKcS0_RDF128_St12chars_format, as older headers declared it.
from_chars_result from_chars(const char *, const char *, _Float128 &, chars_format) noexcept;
}

int main() {
#if defined(_GLIBCXX_HAVE_FLOAT128_MATH) || defined(_GLIBCXX_LDOUBLE_IS_IEEE_BINARY128)
  const char *declared = "declared";
#else
  const char *declared = "not declared";
#endif
  static const char text[] = "1.0000000000000000000000000000007888609052210118054";  // 1 + 2^-100
  _Float128 tiny = 1;
  for (int i = 0; i < 100; ++i)
    tiny /= 2;
  _Float128 value = 0;
  std::from_chars_result r = std::from_chars(text, text + std::strlen(text), value, std::chars_format::general);
  bool parsed = r.ec == std::errc() && r.ptr == text + std::strlen(text);
  const char *precision = value == 1 + tiny ? "113-bit" : value == 1 ? "64-bit (strtold fallback)" : "other";
  std::printf("S9-CXX f128 %s from_chars(_Float128) (%s in <charconv>) reads 1+2^-100 at %s precision\n",
              parsed ? "PASS" : "FAIL", declared, precision);
  return !parsed;
}
