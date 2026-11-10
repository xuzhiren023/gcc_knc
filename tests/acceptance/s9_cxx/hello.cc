// S9-03/S9-04: iostream, strings and containers from libstdc++, linked static and shared.
#include "check.h"
#include <algorithm>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

int main() {
  std::ostringstream os;
  os << 42 << ' ' << 3.5 << ' ' << std::hex << 255 << ' ' << std::string("knc");
  CHECK(os.str() == "42 3.5 ff knc");
  std::istringstream is("7 -2 1e3");
  int a = 0, b = 0;
  double c = 0;
  is >> a >> b >> c;
  CHECK(a == 7 && b == -2 && c == 1000.0);
  std::vector<std::string> v{"pear", "apple", "fig"};
  std::sort(v.begin(), v.end());
  CHECK(v[0] == "apple" && v[2] == "pear");
  std::map<std::string, int> m;
  for (const auto &s : v)
    m[s] = (int)s.size();
  CHECK(m.size() == 3 && m["fig"] == 3);
  std::string big(100000, 'x');
  big += "end";
  CHECK(big.size() == 100003 && big.substr(100000) == "end");
  std::cout << "S9-CXX iostream line" << std::endl;
  CHECK(std::cout.good());
  return report("hello");
}
