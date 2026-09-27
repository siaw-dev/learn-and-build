# 🏛️ Learn & Build — Autonomous Systems Intelligence Vault

> A living, compounding knowledge vault, low-level technical blueprint library, and automated project scaffolder. Curated autonomously across systems engineering, kernel architectures, language runtimes, network protocols, and distributed consensus.

<p align="left">
  <a href="https://siaw-dev.github.io/learn-and-build/"><img src="https://img.shields.io/badge/Live%20Dashboard-GitHub%20Pages-0A66C2?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Live Dashboard" /></a>
  <a href="blueprints/"><img src="https://img.shields.io/badge/Verified%20Blueprints-11-059669?style=for-the-badge" alt="Verified Blueprints" /></a>
  <a href="data/facts.json"><img src="https://img.shields.io/badge/Engineering%20Facts-8-7C3AED?style=for-the-badge" alt="Engineering Facts" /></a>
  <a href="curator/mcp_server.py"><img src="https://img.shields.io/badge/Model%20Context%20Protocol-2024--11--05-2563EB?style=for-the-badge" alt="MCP Server" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-CC0--1.0-10B981?style=for-the-badge" alt="License" /></a>
</p>

---

## 🌐 Interactive Web Dashboard

Explore the entire repository visually via our single-page, zero-dependency Geist design dashboard hosted on GitHub Pages:

👉 **[https://siaw-dev.github.io/learn-and-build/](https://siaw-dev.github.io/learn-and-build/)**

*Features live blueprint markdown rendering, dual-tab facts feed with one-click clipboard copying, domain filters, instant search, and GitHub Actions cloud ingestion triggers.*

---

## 🚀 Quickstart & Tooling

### 1. Instant Project Scaffolder
Extract compilable starter code and build instructions directly from any verified blueprint:
```bash
# Scaffolds idiomatic packages (Rust, Go, Java, C/C++, Python)
vault scaffold tokio --out ./my-tokio-app
vault scaffold libbpf --out ./my-ebpf-loader
vault scaffold raft --out ./my-raft-cluster
```

### 2. Global CLI (`vault`)
```bash
vault list                         # List all indexed technologies & blueprint status
vault search "kprobe"              # Search blueprints by keyword, syscall, or pattern
vault facts                        # View recorded runtime invariants & discoveries
vault fact "<text>" --domain "..." # Record a new cross-project invariant
vault note <slug> "<gotcha>"       # Append a field note to blueprint Section 5
```

### 3. Native Model Context Protocol (MCP) Server
AI agents (Antigravity, Claude Code, Cursor) can directly connect to the vault via stdio JSON-RPC:
```json
{
  "mcpServers": {
    "learn-and-build": {
      "command": "python3",
      "args": ["/path/to/learn-and-build/curator/mcp_server.py"]
    }
  }
}
```
*Exposes 6 tools (`search_blueprints`, `get_blueprint`, `record_field_note`, `record_fact`, `list_vault`, `scaffold_blueprint`) and dynamic resources (`vault://blueprints/{slug}`, `vault://facts`).*

---

## 🧠 Battle-Tested Runtime Invariants & Discoveries

The Learn & Build vault automatically compounds non-obvious engineering facts learned across real projects:

| Domain | Verified Discovery | Tags |
| :--- | :--- | :--- |
| **Kernel & Low-Level Systems** | Linux 6.x kernels require raw eBPF program types to specify GPL compatible licenses | `ebpf` `linux6` |
| **Kernel & Low-Level Systems** | Huawei / Vodafone USB modems (e.g. K4203) enumerate initially as USB Mass Storage (vendor 12d1:1f1c) and require an explicit SCSI eject sequence (55534243123456780000000000000011062000000101000100000000000000) sent via usb_modeswitch to flip into high-speed CDC/serial modem interfaces (12d1:157a). | `usb` `udev` `kernel` `hardware` `modem` |
| **Web Architecture & Protocols** | Running headless browser automation (Puppeteer/Playwright) on ARM Android/Termux fails due to missing glibc/Chromium binaries; headless automation on Android must use raw WebSocket protocol clients (e.g., Baileys) and pure Node.js sockets instead of browser engines. | `termux` `android` `websockets` `puppeteer` `baileys` |
| **Tools, CLI & Utilities** | WhatsApp voice note compatibility requires Opus audio inside an OGG container with a strict sample rate of 48,000 Hz and mono audio channel; sending raw AAC or standard MP3 causes voice notes to render as generic audio files without waveform scrubbing. | `ffmpeg` `audio` `opus` `whatsapp` `transcoding` |
| **Compilers & Language Runtimes** | Dalvik VMP register scrambling using a coprime affine permutation ((r * A + B) % N with gcd(A, N) = 1 seeded by SHA-256) completely destroys linear register flow for decompilers (JEB/Jadx) without register collisions or out-of-bounds wide operations in native execution. | `dalvik` `vmp` `reverse-engineering` `obfuscation` `security` |
| **Kernel & Low-Level Systems** | In embedded and native security loaders, raw C string literals for /proc/, /dev/, or binary magics (dex\n035) are trivially extracted by automated static scanners; strings must be XOR-encoded at compile time and stack buffers immediately wiped using volatile pointer dereferencing (secure_bzero) to prevent compiler dead-code elimination. | `c` `anti-tamper` `memory-safety` `compiler-optimizations` `security` |
| **Kernel & Low-Level Systems** | Samsung File-Based Encryption (FBE) & Knox On-Device Encryption (ODE) Disabling: Attaining unencrypted storage in custom recoveries (TWRP/OrangeFox) requires four synchronized steps: (1) Neutralizing AVB 2.0 / dm-verity via patched vbmeta (flags 0x3) and patched boot/recovery; (2) Disarming vendor fstab forced encryption by replacing fileencryption= and forceencrypt= with encryptable in /vendor/etc/fstab.{qcom,exynos,mt*} and neutralizing recovery-from-boot.p; (3) Executing TWRP 'Format Data' (make_ext4fs/mkfs.f2fs) to destroy ciphertext and recreate an unencrypted filesystem; (4) Wiping Knox ODE partitions (/keydata, /keyrefuge) to eliminate orphan cryptographic tokens that cause reboot loops. | `samsung` `twrp` `fbe` `encryption` `android-root` `odin` `dm-verity` |
| **Android Root & System Optimization** | Samsung Galaxy One UI Core devices on Android 11+ dynamically register IME input methods and home launcher activities. Disabling com.sec.android.app.launcher or com.samsung.android.honeyboard leaves the window manager without a fallback intent receiver, causing SystemUI to drop into a black screen without crash logs. | `samsung` `android11` `oneui` `debloat` `ime` |

---

## 📚 Table of Contents

- [Root Solutions](#root-solutions)
- [Kernel & Low-Level Systems](#kernel-low-level-systems)
- [Compilers & Language Runtimes](#compilers-language-runtimes)
- [Distributed Systems & Storage](#distributed-systems-storage)
- [Web Architecture & Protocols](#web-architecture-protocols)
- [Tools, CLI & Utilities](#tools,-cli-utilities)
- [Other](#other)

---

## Root Solutions

### 📄 [Android Rooting Guide | Awesome Android Root](https://awesome-android-root.zhoe.org/rooting-guides/)

> The ultimate Android rooting guide covering Magisk, KernelSU, APatch installation with device-specific tutorials for Pixel, Samsung, Xiaomi, OnePlus & more.

![Web](https://img.shields.io/badge/-Article-0A66C2?logo=googlechrome&logoColor=white&style=flat-square)
**Status**: 🟢 Active · 👤 Awesome Android Root Project
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/android_rooting_guide___awesome_android_root.md) `vault scaffold android_rooting_guide___awesome_android_root`


---

### 🔧 [awesome-android-root/awesome-android-root](https://github.com/awesome-android-root/awesome-android-root)

> Discover best root apps, Magisk, KernelSu & LSPosed(xposed) modules & rooting guides

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 4,729 · 👤 awesome-android-root
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/awesome-android-root.md) `vault scaffold awesome-android-root`

**Tags**: `android` `android-app` `android-root` `android-tweaks` `apatch` `awesome` `awesome-list` `awesome-resources` `kernel-module` `kernelsu` `kernelsu-module` `kernelsu-next` `lsposed` `magisk` `magisk-manager` `magisk-module` `root` `vitepress` `xposed` `xposed-module`
---

### 🔧 [tiann/KernelSU](https://github.com/tiann/KernelSU)

> A Kernel based root solution for Android

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 18,572 · 👤 tiann
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/kernelsu.md) `vault scaffold kernelsu`

**Tags**: `android` `kernel` `kernelsu` `root` `su`
---

### 🔧 [topjohnwu/Magisk](https://github.com/topjohnwu/Magisk)

> The Magic Mask for Android

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 62,911 · 👤 topjohnwu
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/magisk.md) `vault scaffold magisk`


---


## Kernel & Low-Level Systems

### 🔧 [libbpf/libbpf](https://github.com/libbpf/libbpf)

> Automated upstream mirror for libbpf stand-alone build.

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 2,757 · 👤 libbpf
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/libbpf.md) `vault scaffold libbpf`

**Tags**: `bpf` `libbpf` `tracing` `kernel` `eBPF`**Category**: Linux Kernel

---


## Compilers & Language Runtimes

### 🔧 [bytecodealliance/wasmtime](https://github.com/bytecodealliance/wasmtime)

> A lightweight WebAssembly runtime that is fast, secure, and standards-compliant

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 18,656 · 👤 bytecodealliance
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/wasmtime.md) `vault scaffold wasmtime`

**Tags**: `webassembly` `wasm` `runtime` `rust` `cranelift` `jit` `sandbox`**Category**: JIT Compilers

---

### 🔧 [tokio-rs/tokio](https://github.com/tokio-rs/tokio)

> A runtime for writing reliable asynchronous applications with Rust. Provides I/O, networking, scheduling, timers, ...

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 33,228 · 👤 tokio-rs
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/tokio.md) `vault scaffold tokio`

**Tags**: `rust` `asynchronous` `runtime` `networking` `concurrency` `io`**Category**: Bytecode VMs

---


## Distributed Systems & Storage

### 🔧 [hashicorp/raft](https://github.com/hashicorp/raft)

> Golang implementation of the Raft consensus protocol

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 9,136 · 👤 hashicorp
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/raft.md) `vault scaffold raft`

**Tags**: `raft` `consensus` `distributed systems` `golang` `replicated state machine` `replication`**Category**: Consensus Protocols

---


## Web Architecture & Protocols

### 🔧 [lysine-dev/retrofit](https://github.com/square/retrofit)

> A type-safe HTTP client for Android and the JVM

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 43,944 · 👤 square
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/retrofit.md) `vault scaffold retrofit`

**Tags**: `retrofit` `http-client` `android` `java` `networking` `rest-api`**Category**: HTTP Clients

---


## Tools, CLI & Utilities

### 🔧 [google/guava](https://github.com/google/guava)

> Google core libraries for Java

![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)
**Status**: 🟢 Active · ⭐ 51,908 · 👤 google
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/guava.md) `vault scaffold guava`

**Tags**: `guava` `java`
---


## Other

### 📄 [Android Root Apps, Modules & Rooting Guides | Awesome Android Root](https://awesome-android-root.zhoe.org/)

> Browse 650+ Android root apps and modules, practical rooting guides, and troubleshooting help for rooted devices.

![Web](https://img.shields.io/badge/-Article-0A66C2?logo=googlechrome&logoColor=white&style=flat-square)
**Status**: 🟢 Active
**Blueprint**: [📐 **View Architectural Blueprint & Recipes**](blueprints/android_root_apps__modules___rooting_guides___awesome_android_root.md) `vault scaffold android_root_apps__modules___rooting_guides___awesome_android_root`


---



---

<details>
<summary>📖 About the Learn & Build Architecture</summary>

The **Learn & Build** engine is an autonomous engineering intelligence ecosystem:
1. **Source Ingestion**: Ingests GitHub repositories, technical RFCs, and documentation via cloud GitHub Actions or local CLI.
2. **Deep Blueprint Synthesis**: Gemini models extract full 5-section blueprints (Architectural Topology, Low-Level Mechanics, Data Contracts, Production Scaffolding Boilerplate, and Invariants/Gotchas).
3. **Automated Scaffolding**: AST/markdown parsers reconstruct idiomatic directory hierarchies from blueprint recipes.
4. **Autonomous Memory Compounding**: Every project built in the workspace records verified runtime quirks directly back into the vault.

To ingest a new repository:
```bash
python3 ingest.py ingest --url <repository-url> --store json
python3 ingest.py render --store json
```
</details>

*Last updated: auto-generated · 11 entries across 7 categories · 8 runtime facts · 11 verified blueprints*