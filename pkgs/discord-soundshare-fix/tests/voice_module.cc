#include <cstdint>

asm(R"(
  .text
  .globl _ZN7discord5media9LocalUser18SignalOnSoundshareEb
  .type _ZN7discord5media9LocalUser18SignalOnSoundshareEb, @function
_ZN7discord5media9LocalUser18SignalOnSoundshareEb:
  push %r14
  push %rbx
  sub $0x18, %rsp
  mov %rdi, %rbx
  mov %sil, 0xf(%rsp)
  .byte 0x40, 0x88, 0xb7, 0x30, 0x1f, 0x00, 0x00
  incl 0x1f34(%rbx)
  add $0x18, %rsp
  pop %rbx
  pop %r14
  ret
  .size _ZN7discord5media9LocalUser18SignalOnSoundshareEb, .-_ZN7discord5media9LocalUser18SignalOnSoundshareEb

  .globl _ZN7discord5media9LocalUser23SignalOnSoundshareEndedEv
  .type _ZN7discord5media9LocalUser23SignalOnSoundshareEndedEv, @function
_ZN7discord5media9LocalUser23SignalOnSoundshareEndedEv:
  push %r14
  push %rbx
  push %rax
  mov %rdi, %rbx
  .byte 0xc6, 0x87, 0x30, 0x1f, 0x00, 0x00, 0x00
  incl 0x1f34(%rbx)
  pop %rax
  pop %rbx
  pop %r14
  ret
  .size _ZN7discord5media9LocalUser23SignalOnSoundshareEndedEv, .-_ZN7discord5media9LocalUser23SignalOnSoundshareEndedEv
)");

extern "C" void _ZN7discord5media9LocalUser18SignalOnSoundshareEb(void*, bool);
extern "C" void _ZN7discord5media9LocalUser23SignalOnSoundshareEndedEv(void*);

struct alignas(16) FakeLocalUser {
  std::uint8_t bytes[0x2000] = {};
};

static FakeLocalUser user;

static int restarts() {
  return *reinterpret_cast<const int*>(user.bytes + 0x1f34);
}

extern "C" __attribute__((visibility("default"))) int fixture_signal(int success) {
  _ZN7discord5media9LocalUser18SignalOnSoundshareEb(&user, success != 0);
  return restarts();
}

extern "C" __attribute__((visibility("default"))) int fixture_end() {
  _ZN7discord5media9LocalUser23SignalOnSoundshareEndedEv(&user);
  return restarts();
}

extern "C" __attribute__((visibility("default"))) int fixture_active() {
  return user.bytes[0x1f30];
}
