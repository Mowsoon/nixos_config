#include <dlfcn.h>
#include <cstdint>
#include <cstdio>
#include <cstring>

template <typename T>
T Lookup(void* module, const char* name) {
  void* symbol = dlsym(module, name);
  T function = nullptr;
  std::memcpy(&function, &symbol, sizeof(function));
  return function;
}

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  void* module = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (module == nullptr) {
    std::fprintf(stderr, "dlopen: %s\n", dlerror());
    return 3;
  }
  auto signal = Lookup<int (*)(int)>(module, "fixture_signal");
  auto end = Lookup<int (*)()>(module, "fixture_end");
  auto active = Lookup<int (*)()>(module, "fixture_active");
  using Status = int (*)(std::uint64_t*, std::uint64_t*);
  auto status = Lookup<Status>(RTLD_DEFAULT, "discord_soundshare_fix_status_v1");

  struct Step { const char* name; int value; int flag; } steps[7];
  steps[0] = {"start", signal(1), active()};
  steps[1] = {"duplicate start", signal(1), active()};
  steps[2] = {"ended", end(), active()};
  steps[3] = {"start after ended", signal(1), active()};
  steps[4] = {"stop", signal(0), active()};
  steps[5] = {"start after stop", signal(1), active()};
  steps[6] = {"duplicate start", signal(1), active()};
  for (const auto& step : steps) std::printf("%-18s restarts=%d flag=%d\n", step.name, step.value, step.flag);
  std::uint64_t hits = 0, blocked = 0;
  const int state = status ? status(&hits, &blocked) : -1;
  std::printf("hook state=%d hits=%llu blocked=%llu\n", state, (unsigned long long)hits, (unsigned long long)blocked);
  const int expected[7] = {1, 1, 2, 3, 4, 5, 5};
  for (int i = 0; i < 7; ++i) if (steps[i].value != expected[i]) return 10 + i;
  return (state == 1 && hits == 6 && blocked == 2) ? 0 : 9;
}
