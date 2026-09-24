# Blueprint: Android Rooting Guide | Awesome Android Root

> **Source**: [https://awesome-android-root.zhoe.org/rooting-guides/](https://awesome-android-root.zhoe.org/rooting-guides/)  
> **Domain / Category**: Root Solutions  
> **Core Architectural Purpose**: This system establishes administrative (`UID 0`) control over the Android OS by intercepting and modifying boot image execution chains (`boot.img` / `init_boot.img`), injecting kernel-level hooks or user-space daemon overlays (`Magisk`, `KernelSU`, `APatch`), and enforcing fine-grained policy-based privilege escalation (`su`) while bypassing modern security enclaves (SELinux, AVB, Play Integrity).

---

## 1. Architectural Topology & Entry Points
- **System Boundaries**: 
  - *User-space to Daemon*: Android apps communicate with the root manager daemon via Unix domain sockets using credential passing (`SO_PEERCRED`) to verify process UID/PID and package name bindings.
  - *Kernel to User-space*: KernelSU and APatch leverage kernel-space hooks (sys_call_table, kprobes, or inline assembly hooks) to intercept system calls from untrusted domains, dynamically pivoting process credentials (`struct cred`) into `UID 0` and permissive SELinux contexts (`u:r:su:s0`).
  - *Bootchain Initialization*: The bootloader verifies and loads `boot.img` / `init_boot.img`. The modified init binary mounts dynamic overlay filesystems (`Magic Mount` / `OverlayFS`) before executing `init`, replacing standard system binaries (`su`, `magiskd`) into memory streams.
- **Directory & Component Map**:
  - `/dev/` / `/sys/`: Kernel-level hooks export pseudo-filesystems or character devices for user-space control panels.
  - `/data/adb/`: Persistent storage root for root management binaries, modules, scripts, and module overlay directories (`/data/adb/modules/`).
  - `/init` / `init.rc`: First-stage user-space initialization script modified to bootstrap the root daemon prior to mounting storage partitions.
- **Lifecycle & Execution Flow**:
  1. **Cold Boot / Fastboot Flashing**: The user flashes a modified `boot.img` or `init_boot.img` containing an exploited or patched ramdisk.
  2. **Init Stage**: The modified `init` binary parses custom configuration files, spawns the core root daemon (`magiskd` or `ksud`), and configures loop devices for module overlay mounting.
  3. **Daemon Initialization**: The root daemon starts listening on internal IPC sockets and drops privileges where necessary while maintaining a secure administrative bridge.
  4. **App Request (`su`)**: An app executes the `su` binary. The binary passes arguments and context over the IPC socket to the daemon, which prompts the user (or evaluates an automated policy profile) and patches the calling process's kernel credential structure upon approval.

---

## 2. Core Mechanisms, Algorithms & Low-Level Techniques
- **Fundamental Invariants**: 
  - *Credential Mutation*: Root implementations locate the calling process's task structure (`struct task_struct`) in kernel memory, traverse to its credential structure (`struct cred`), and overwrite `uid`, `gid`, `suid`, `sgid`, `euid`, `egid`, `fsuid`, `fsgid`, and capability sets (`cap_effective`, `cap_permitted`, `cap_inheritable`) with zero-privilege or full-privilege bitmasks.
  - *OverlayFS / Magic Mount*: Systemless modifications avoid writing directly to the read-only read-only block devices (`/system`, `/product`, `/vendor`). Instead, they use overlay filesystems to mount writable tmpfs/loop directories over the target mount points dynamically during early init.
- **Subsystem Interfacing**:
  - *Kernel Patching (KernelSU/APatch)*: KernelSU compiles directly into the kernel source or is injected via Kernel Patch Management (KPM). It hooks kernel functions using `kprobes` or direct function patching to intercept `sys_execve` or security checks like `selinux_enforcing` and `inode_permission`.
  - *SELinux Policy Bypass*: To prevent the restricted SELinux domain from blocking administrative operations, root daemons patch the in-kernel SELinux policy state (`selinux_enforcing` variable or vector lookup tables) or transition the calling process into an unrestricted context (`u:r:su:s0` or `u:r:kernel:s0`).
- **Security & Integrity Model**:
  - *Play Integrity & Hardware Attestation*: Google's Play Integrity verifies bootloader lock status, AVB (Android Verified Boot) state, and device certificate chains. Unlocking the bootloader or modifying partitions causes `deviceIntegrity` and `meetsStrongIntegrity` to fail. Root solutions deploy runtime hiding mechanisms (zygisk, mounting namespace unlinking, process name obfuscation, property hiding) to evade user-space detection heuristics by banking and enterprise applications.

---

## 3. Data Contracts, Structs & Core API Signatures
Below are low-level C and Rust structural blueprints representing how root daemons and kernel drivers interact with process credentials and system call interceptions.

### Kernel Credential Struct Modification (C / Linux Kernel)
```c
#include <linux/cred.h>
#include <linux/sched.h>
#include <linux/uidgid.h>

// Structural representation of credential escalation logic executed by KernelSU/APatch/Magisk
int elevate_process_credentials(struct task_struct *task) {
    struct cred *new_cred;
    kuid_t root_uid = KUIDT_INIT(0);
    kgid_t root_gid = KGIDT_INIT(0);

    // Prepare mutable credential structures
    new_cred = prepare_creds();
    if (!new_cred)
        return -ENOMEM;

    // Overwrite User and Group Identifiers to root (0)
    new_cred->uid = root_uid;
    new_cred->suid = root_uid;
    new_cred->euid = root_uid;
    new_cred->fsuid = root_uid;

    new_cred->gid = root_gid;
    new_cred->sgid = root_gid;
    new_cred->egid = root_gid;
    new_cred->fsgid = root_gid;

    // Grant full capability sets for administrative execution
    cap_set_full(&new_cred->cap_effective);
    cap_set_full(&new_cred->cap_permitted);
    cap_set_full(&new_cred->cap_inheritable);
    cap_set_full(&new_cred->cap_bset);
    cap_set_full(&new_cred->cap_ambient);

    // Commit the overridden credentials to the target task
    return commit_creds(new_cred);
}
```

### IPC Socket Request Payload Protocol (Rust / User-space Daemon)
```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct SuRequest {
    pub uid: u32,
    pub pid: u32,
    pub target_uid: u32,
    pub command: String,
    pub package_name: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub enum SuResponse {
    Allow,
    Deny,
    Error { message: String },
}

pub trait RootIpcServer {
    fn handle_connection(&self, stream: &mut dyn std::io::Read) -> Result<SuResponse, std::io::Error>;
}
```

---

## 4. Production-Ready Scaffolding Boilerplate (Copy-Paste)
The following Python script automates the verification, extraction, and patch generation pipeline for an Android boot image (`boot.img` or `init_boot.img`) using standard unpack/repack algorithms compatible with modern root solutions.

```python
#!/usr/bin/env python3
"""
Android Boot Image Patcher & Root Integration Boilerplate
Extracts boot/init_boot headers, parses ramdisk structures, and prepares for root payload injection.
"""

import os
import sys
import struct
import subprocess
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"

class BootImageHeader:
    def __init__(self, data: bytes):
        if not data.startswith(BOOT_MAGIC):
            raise ValueError("Invalid boot image magic signature.")
        self.magic = data[0:8]
        self.kernel_size = struct.unpack("<I", data[8:12])[0]
        self.kernel_addr = struct.unpack("<I", data[12:16])[0]
        self.ramdisk_size = struct.unpack("<I", data[16:20])[0]
        self.ramdisk_addr = struct.unpack("<I", data[20:24])[0]

def analyze_boot_image(image_path: Path):
    print(f"[*] Analyzing boot image: {image_path}")
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(image_path, "rb") as f:
        header_data = f.read(2048) # Read standard boot header block
        
    try:
        header = BootImageHeader(header_data)
        print(f"[+] Magic: {header.magic.decode('utf-8', errors='ignore')}")
        print(f"[+] Kernel Size: {header.kernel_size} bytes")
        print(f"[+] Ramdisk Size: {header.ramdisk_size} bytes")
    except Exception as e:
        print(f"[-] Failed to parse standard boot header: {e}")
        print("[*] Image may utilize vendor_boot, init_boot, or signed proprietary headers.")

def verify_environment():
    tools = ["adb", "fastboot"]
    for tool in tools:
        res = subprocess.run(["which", tool], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[-] Critical dependency missing: {tool}")
            sys.exit(1)
        print(f"[+] Found system tool: {tool} -> {res.stdout.strip()}")

if __name__ == "__main__":
    print("--- Android Root System Scaffolding ---")
    verify_environment()
    
    if len(sys.argv) > 1:
        target_image = Path(sys.argv[1])
        analyze_boot_image(target_image)
    else:
        print("[*] Usage: python3 patch_boot.py </path/to/boot.img>")
```

---

## 5. Engineering Invariants, Tradeoffs & Gotchas
- **Performance & Concurrency Characteristics**:
  - *Context Switching & IPC Overhead*: Intercepting system calls or routing `su` requests through user-space daemons via Unix sockets incurs slight execution latency during process creation (`fork`/`exec`). Kernel-level solutions (KernelSU) minimize this by handling permission checks entirely in kernel space.
  - *Memory Footprint*: Magic Mount and OverlayFS consume small amounts of kernel memory for tracking dynamic dentries and mount tables.
- **Failure Modes & Edge Cases**:
  - *Bootloops*: Incorrect ramdisk modifications, corrupted gzip/lz4 compression headers in `boot.img`, or incompatible SELinux policy rules result in early boot crashes (bootloops). *Mitigation*: Always retain an unedited stock firmware dump and know hardware key combinations to enter Fastboot / Odin / EDL recovery modes.
  - *Knox / Hardware Fuse Triggers (Samsung)*: Unlocking the bootloader on Samsung devices permanently blows a physical eFuse (Knox). This action irreversibly disables hardware-backed features (Samsung Pay, Secure Folder, Pass) even if the bootloader is subsequently re-locked and stock firmware is restored.
  - *OTA Updates*: Applying Over-The-Air (OTA) system updates overwrites modified partition blocks (`boot.img`, `init_boot`). Users must restore stock boot images, apply the OTA update, and re-patch the updated boot image before rebooting.
- **Hard Prerequisites**:
  - Host machine with Android Platform Tools (`adb` / `fastboot`).
  - Target device with an unlockable bootloader (carrier-locked variants typically lack OEM unlocking toggles).
  - Exact matching stock firmware package (`boot.img` or `init_boot.img`) corresponding precisely to the device's currently installed software build number.