# Blueprint: google/guava

> **Source**: [https://github.com/google/guava](https://github.com/google/guava)  
> **Domain / Category**: Java Core Libraries & Systems Utilities  
> **Core Architectural Purpose**: Guava provides an optimized, production-grade extension to the standard Java Collections Framework, concurrency primitives, I/O utilities, primitive wrappers, and caching mechanisms. It achieves this by enforcing strict immutability semantics, zero-copy structural sharing, highly optimized hash-based routing, and predictable garbage collection behavior via pre-allocated and memory-efficient data structures.

---

## 1. Architectural Topology & Entry Points
- **System Boundaries**: Operates entirely within the Java Virtual Machine (JVM) memory space. It interacts with the underlying OS through standard Java Native Interface (JNI) abstractions, standard NIO system calls (channels, selectors), and standard multi-threading primitives (`java.util.concurrent` locks, atomic variables, and `Unsafe` memory management where applicable).
- **Directory & Component Map**:
  - `com.google.common.collect`: Immutable collections (`ImmutableList`, `ImmutableMap`), `Multimap`, `Multiset`, `BiMap`, and specialized concurrent collections.
  - `com.google.common.cache`: High-performance local caching engine implementing LRU, size-based, and time-based eviction with concurrent segmented striping (`LocalCache`).
  - `com.google.common.util.concurrent`: Synchronization utilities (`ListenableFuture`, `MoreExecutors`, rate limiters, striping locks).
  - `com.google.common.io`: Byte/character stream utilities, files, and source/sink abstractions.
  - `com.google.common.hash`: Hashing frameworks (`Murmur3`, `CityHash`, Bloom filters).
  - `com.google.common.primitives`: Unsigned primitive utilities and memory-efficient array wrappers.
- **Lifecycle & Execution Flow**: Initialization is static or factory-method driven (e.g., `ImmutableList.of()`, `CacheBuilder.newBuilder()`). There are no long-running daemons inherent to Guava core collections; execution flow is synchronous or reactive via functional transformations (`Function`, `Predicate`, `FluentIterable`) and asynchronous composition via `ListenableFuture` callbacks executed on direct or dedicated thread pools.

---

## 2. Core Mechanisms, Algorithms & Low-Level Techniques
- **Fundamental Invariants**:
  - *Null-Hostility*: Most Guava collections and utilities explicitly reject `null` values to eliminate ambiguity between "key not found" and "key maps to a null value", failing fast with `NullPointerException`.
  - *Defensive Copying & Immutability*: Immutable collections store data in pre-sized, backing arrays without wrapper overhead, providing O(1) random access and thread safety without synchronization overhead.
  - *Striped Concurrency*: `Striped<Lock>` and `LocalCache` use power-of-two hash striping to minimize lock contention across concurrent updates without incurring the penalty of global locks.
- **Subsystem Interfacing**: Leverages low-level JVM intrinsics (e.g., `sun.misc.Unsafe` or `VarHandle` depending on the JDK version) for atomic operations, volatile field access, and off-heap memory safety checks. I/O abstractions (`ByteSource`, `CharSource`) wrap standard Java streams with guaranteed resource lifecycle management (try-with-resources semantics).
- **Security & Integrity Model**: Cryptographic and non-cryptographic hashing algorithms (`Hashing.sha256()`, `Hashing.murmur3_128()`) utilize optimized byte-buffer manipulation to resist collisions and provide fast indexing for distributed caches and Bloom filters.

---

## 3. Data Contracts, Structs & Core API Signatures

```java
package com.google.common.collect;

import java.util.Collection;
import java.util.Map;
import java.util.Set;

public interface ImmutableList<E> extends java.util.List<E>, java.io.Serializable {
    static <E> ImmutableList<E> of();
    static <E> ImmutableList<E> of(E e1);
    static <E> ImmutableList<E> of(E e1, E e2);
    static <E> ImmutableList<E> copyOf(Collection<? extends E> elements);
    
    @Deprecated
    default boolean add(E e) { throw new UnsupportedOperationException(); }
}

package com.google.common.util.concurrent;

import java.util.concurrent.Executor;
import java.util.concurrent.Future;

public interface ListenableFuture<V> extends Future<V> {
    void addListener(Runnable listener, Executor executor);
}

package com.google.common.cache;

import java.util.concurrent.ExecutionException;

public interface LoadingCache<K, V> extends com.google.common.cache.Cache<K, V> {
    V get(K key) throws ExecutionException;
    V getUnchecked(K key);
    void refresh(K key);
}
```

---

## 4. Production-Ready Scaffolding Boilerplate (Copy-Paste)

```java
package com.example.guava.bootstrap;

import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.collect.ImmutableList;
import com.google.common.util.concurrent.*;

import java.time.Duration;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.logging.Level;
import java.util.logging.Logger;

public final class GuavaSystemBootstrap {
    private static final Logger LOGGER = Logger.getLogger(GuavaSystemBootstrap.getName());

    // 1. Define a striped loading cache with automated TTL and size eviction
    private final LoadingCache<String, ImmutableList<String>> dataCache = CacheBuilder.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(Duration.ofMinutes(10))
            .concurrencyLevel(Runtime.getRuntime().availableProcessors())
            .recordStats()
            .build(new CacheLoader<>() {
                @Override
                public ImmutableList<String> load(String key) throws Exception {
                    return fetchRemoteData(key);
                }
            });

    // 2. Define an asynchronous execution engine
    private final ListeningExecutorService backgroundExecutor = 
            MoreExecutors.listeningDecorator(Executors.newFixedThreadPool(4));

    private ImmutableList<String> fetchRemoteData(String key) throws Exception {
        // Simulating low-level data fetch or I/O boundary
        Thread.sleep(50);
        return ImmutableList.of("Record-A-" + key, "Record-B-" + key);
    }

    public ListenableFuture<ImmutableList<String>> processAsync(String key) {
        return backgroundExecutor.submit(() -> {
            try {
                return dataCache.get(key);
            } catch (Exception e) {
                LOGGER.log(Level.SEVERE, "Failed to resolve cache entry for key: " + key, e);
                throw new RuntimeException(e);
            }
        });
    }

    public void shutdown() {
        backgroundExecutor.shutdown();
    }

    public static void main(String[] args) {
        GuavaSystemBootstrap bootstrap = new GuavaSystemBootstrap();
        
        ListenableFuture<ImmutableList<String>> futureResult = bootstrap.processAsync("tenant-alpha");

        Futures.addCallback(futureResult, new FutureCallback<>() {
            @Override
            public void onSuccess(ImmutableList<String> result) {
                LOGGER.info("Successfully retrieved records: " + result);
                bootstrap.shutdown();
            }

            @Override
            public void onFailure(Throwable t) {
                LOGGER.log(Level.SEVERE, "Execution failed", t);
                bootstrap.shutdown();
            }
        }, MoreExecutors.directExecutor());
    }
}
```

---

## 5. Engineering Invariants, Tradeoffs & Gotchas
- **Performance & Concurrency Characteristics**:
  - *Immutable Collections*: Avoid object header overhead and internal node allocations found in standard `java.util.ArrayList` or `HashMap` resizes, trading construction time for optimal O(1) read latency and thread safety without monitor locks.
  - *Cache Segment Locking*: `LocalCache` uses concurrency striping (default 4 segments, configurable up to 65536) to prevent thread bottlenecks during concurrent reads and writes, avoiding global synchronization.
- **Failure Modes & Edge Cases**:
  - *Null Pointer Exception Cascades*: Passing `null` to any Guava collection builder, function application, or map wrapper results in an immediate `NullPointerException`. Guard clauses or `Optional<T>` must be used explicitly.
  - *ClassLoader Leaks*: Caches holding references to classloaders or dynamic types via strong keys/values can cause severe metaspace memory leaks if explicit weak/soft reference keys (`weakKeys()`, `softValues()`) are not configured.
- **Hard Prerequisites**: 
  - Minimum Java Runtime Environment (JRE) 8+ (JRE flavor) or Android SDK 21+ (Android flavor).
  - Proper module path configuration (`module-info.java` requires `com.google.common`).