// S9-03 (--with-libstdcxx-zoneinfo=static): std::chrono time zones need no tzdata on the card.
// C++20, GCC 16 only.
#include "check.h"
#include <chrono>

int main() {
  using namespace std::chrono;
  const time_zone *ny = nullptr;
  try {
    ny = locate_zone("America/New_York");
  } catch (...) {
  }
  CHECK(ny != nullptr);
  if (ny) {
    sys_seconds summer = sys_days{year{2026} / July / 1} + hours{16};
    sys_seconds winter = sys_days{year{2026} / January / 15} + hours{16};
    CHECK(ny->get_info(summer).offset == hours{-4});
    CHECK(ny->get_info(winter).offset == hours{-5});
    CHECK(ny->to_local(summer).time_since_epoch() == summer.time_since_epoch() - hours{4});
  }
  return report("tz");
}
