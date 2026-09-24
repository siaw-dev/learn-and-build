# Blueprint: KernelSU (Kernel-Based Root Solution)

> **Source**: [https://github.com/tiann/KernelSU](https://github.com/tiann/KernelSU)  
> **Category**: Root Solutions  
> **Role in Ecosystem**: Next-generation root solution for Android running inside kernel space rather than modifying userspace init files, making it virtually undetectable to userspace anti-root checks.

---

## 1. Architectural Layout & Entry Points

- **Kernel Driver (`kernel/`)**:
  - Resides directly in Linux kernel tree or loaded via LKM (Loadable Kernel Module).
  - Main driver initialization in `kernel/core_hook.c` and `kernel/ksu.c`.
- **Userspace Daemon (`userspace/ksud/`)**:
  - Single static binary `ksud` injected into `/system/bin` or mounted via tmpfs.
  - Handles module management, post-fs-data triggers, and su daemon calls.
- **Management App (`manager/`)**:
  - Android APK communicating with the kernel driver via syscall or ioctl interfaces.

---

## 2. Low-Level Mechanics & Hooking Techniques

### Kernel Hooking via Kprobes
KernelSU hooks critical kernel functions directly using Linux `kprobes` (or manual inline assembly hooks for non-GKI):
- **Syscall Interception (`execve`)**:
  - Hooks `do_execveat_common` or `sys_execve`.
  - When a process executes `/system/bin/su`, KernelSU intercepts the call before userspace permissions or SELinux policies check it.
- **Permission Elevation**:
  - Alters the calling task's credentials (`struct cred`) directly in kernel memory:
  ```c
  commit_creds(prepare_kernel_cred(NULL));
  ```
  - Resets capabilities (`cap_effective`, `cap_permitted`, `cap_inheritable`) to `CAP_FULL_SET`.
- **Systemless Module Mounting via OverlayFS**:
  - Uses Linux `overlayfs` to merge `/data/adb/modules/<mod>/system` over `/system`, avoiding any partition modification on modern `erofs` or `read-only` system partitions.

---

## 3. Core API Signatures & Data Structures

### Kernel Interface (Ioctl / Syscall)
KernelSU uses a dedicated magic syscall number or an ioctl device node:

```c
#define KSU_MAGIC 0xDEADBEEF
#define KSU_CMD_GET_VERSION 1
#define KSU_CMD_GRANT_ROOT   2
#define KSU_CMD_ALLOW_SU     3

struct ksu_cred {
    uid_t uid;
    gid_t gid;
    bool  is_root;
};

// Check if KernelSU is present in running kernel
static inline bool is_kernelsu_active(void) {
    long ret = syscall(__NR_prctl, KSU_MAGIC, KSU_CMD_GET_VERSION, 0, 0, 0);
    return ret >= 0;
}
```

---

## 4. Copy-Paste Code Recipes & Boilerplate

### Minimal C Root Escalation Client

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <sys/prctl.h>

#define KSU_MAGIC 0xDEADBEEF
#define KSU_CMD_GRANT_ROOT 2

int main(int argc, char *argv[]) {
    printf("[*] Attempting KernelSU root escalation...\n");

    // Request root elevation from kernel driver
    long ret = syscall(__NR_prctl, KSU_MAGIC, KSU_CMD_GRANT_ROOT, 0, 0, 0);
    if (ret != 0) {
        fprintf(stderr, "[-] KernelSU not detected or request denied.\n");
        return 1;
    }

    if (getuid() == 0) {
        printf("[+] Success! Running with UID 0 (root).\n");
        system("/bin/sh");
    } else {
        printf("[-] Elevation failed.\n");
    }
    return 0;
}
```

### Minimal KernelSU Module Structure (`module.prop`)

```ini
id=my_custom_hook
name=Custom System Hook Module
version=v1.0.0
versionCode=100
author=siaw-dev
description=Demonstrates KernelSU overlayfs module hooking for system binaries.
```

---

## 5. Compatibility Matrix & Engineering Gotchas

- **Kernel Versions**:
  - GKI (Generic Kernel Image): Android 12 (Kernel 5.10), Android 13 (Kernel 5.15), Android 14 (Kernel 6.1).
  - Legacy/Non-GKI: Requires patching kernel source with `kprobes` backports before building boot image.
- **SELinux Gotchas**:
  - Because credential escalation happens at kernel level, userspace SELinux domain transition (`u:r:su:s0`) must still match permissive rules injected into `/sys/fs/selinux`.
- **Evasion**:
  - Zero su binary traces in standard paths unless granted; Play Integrity hardware attestation requires Keymint/TEE patches.
