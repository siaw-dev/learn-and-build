# Blueprint: Magisk & Zygisk (Systemless Root & Runtime Injection)

> **Source**: [https://github.com/topjohnwu/Magisk](https://github.com/topjohnwu/Magisk)  
> **Category**: Root Solutions  
> **Role in Ecosystem**: The industry-standard systemless root framework and runtime code execution platform for Android via boot image patching and Zygote injection (Zygisk).

---

## 1. Architectural Layout & Entry Points

- **`magiskboot`**:
  - Unpacks, modifies, and repacks `boot.img` (kernel + ramdisk).
  - Patches `init` binary to replace it with `magiskinit`.
- **`magiskinit` (Early Boot Hijack)**:
  - First code executed by kernel when mounting rootfs.
  - Mounts early overlays, hijacks `init.rc`, and loads `magiskpolicy`.
- **`magiskd` (The Core Daemon)**:
  - Superuser provider (`/system/bin/su`).
  - Manages module lifecycles: `post-fs-data`, `service.sh`.
- **`zygisk` (Zygote In-Process Hooking)**:
  - Injects a shared library (`.so`) into Android's `app_process` (Zygote) before any app is forked.

---

## 2. Low-Level Mechanics & Hooking Techniques

### Zygote Fork Interception (Zygisk)
Zygisk uses PLT/GOT hooking or inline hooks (via Dobby/ShadowHook) to intercept native Zygote JNI calls:
- **Pre-Fork (`forkAndSpecializePre`)**:
  - Runs inside the master Zygote process.
  - Checks UID, package name, and isolate process flags.
- **Post-Fork (`forkAndSpecializePost`)**:
  - Runs inside the newly created app process immediately after fork.
  - Unmounts root binaries or modules if the app is on the "DenyList" (anti-detection).
  - Can load ART/Java hooks or native hooks into the app runtime.

### Dynamic SELinux Policy Injection (`magiskpolicy`)
- Directly patches SELinux rules in kernel memory (`/sys/fs/selinux/load`):
  ```bash
  magiskpolicy --live "allow su * * *"
  ```

---

## 3. Core API Signatures & Data Structures

### Zygisk Module C++ API (`zygisk.hpp`)

```cpp
#include <jni.h>

namespace zygisk {
    class ModuleBase {
    public:
        virtual void onLoad(void *handle, void *env) {}
        virtual void preAppSpecialize(AppSpecializeArgs *args) {}
        virtual void postAppSpecialize(const AppSpecializeArgs *args) {}
        virtual void preServerSpecialize(ServerSpecializeArgs *args) {}
        virtual void postServerSpecialize(const ServerSpecializeArgs *args) {}
    };

    struct AppSpecializeArgs {
        jint &uid;
        jint &gid;
        jintArray &gids;
        jint &runtime_flags;
        jobjectArray &rlimits;
        jint &mount_external;
        jstring &se_info;
        jstring &nice_name;
        jboolean &is_child_zygote;
        jstring &instruction_set;
        jstring &app_data_dir;
    };
}
```

---

## 4. Copy-Paste Code Recipes & Boilerplate

### Minimal Zygisk Native Module (`module.cpp`)

```cpp
#include <android/log.h>
#include <unistd.h>
#include "zygisk.hpp"

#define LOG_TAG "MyZygiskModule"
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)

class MyModule : public zygisk::ModuleBase {
public:
    void onLoad(void *handle, void *env) override {
        LOGD("Module loaded into Zygote PID: %d", getpid());
    }

    void preAppSpecialize(zygisk::AppSpecializeArgs *args) override {
        // Inspect process before privilege drop
    }

    void postAppSpecialize(const zygisk::AppSpecializeArgs *args) override {
        LOGD("App specialized! Process running with UID: %d", getuid());
        // Insert runtime hooks or memory modifications here
    }
};

REGISTER_ZYGISK_MODULE(MyModule)
```

### Module Package Layout

```text
my-zygisk-module/
├── module.prop
├── zygisk/
│   ├── arm64-v8a.so
│   └── armeabi-v7a.so
└── post-fs-data.sh
```

---

## 5. Compatibility Matrix & Engineering Gotchas

- **Android Versions**:
  - Android 5.0 through Android 15.
  - Android 12+ requires Zygisk (Riru is deprecated).
- **Zygote Isolation**:
  - In Android 10+, isolated processes (e.g., Chrome renderers) run in tightly constrained seccomp filters. Modifying memory in these processes will trigger SIGSYS unless filtered.
- **DenyList Pitfall**:
  - When Magisk DenyList is enabled for an app, Zygisk is completely unloaded from that process; modules cannot hook DenyListed apps.
