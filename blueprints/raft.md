# Blueprint: hashicorp/raft

> **Source**: [https://github.com/hashicorp/raft](https://github.com/hashicorp/raft)  
> **Domain / Category**: Distributed Systems & Storage  
> **Core Architectural Purpose**: Provides a robust, thread-safe, and pure Go implementation of the Raft consensus protocol. It manages a replicated log and interfaces with a Finite State Machine (FSM) to ensure strongly consistent, partition-tolerant (CP) distributed state replication across networked nodes.

---

## 1. Architectural Topology & Entry Points
- **System Boundaries**: 
  - Network I/O is decoupled via a `Transport` interface (supporting TCP-based `NetworkTransport` or in-memory equivalents) using custom RPC payload serializations (Msgpack via `github.com/hashicorp/go-msgpack/v2`).
  - Persistent state (logs and metadata) is decoupled via `LogStore` and `StableStore` interfaces (with backing stores like `raft-boltdb` or `raft-mdb`).
  - Snapshotting delegates state serialization to the FSM and writes storage layers via `SnapshotStore` interfaces.
- **Directory & Component Map**:
  - `api.go`, `config.go`, `configuration.go`: Core entry points, configurations, and peer management interfaces.
  - `raft.go` (implied base): Main consensus event loop, leader/follower/candidate state management.
  - `log.go`, `log_cache.go`: Log entry abstractions and optimization caching layers.
  - `net_transport.go`: Production TCP transport layer implementation using connection pools.
  - `fsm.go`: Finite State Machine execution interfaces.
  - `file_snapshot.go`, `inmem_snapshot.go`: Snapshot persistence engines.
  - `commitment.go`, `progress.go`: Replication tracking and commit index advancement calculations.
- **Lifecycle & Execution Flow**:
  1. **Initialization**: Instantiate `Config`, supply `LogStore`, `StableStore`, `SnapshotStore`, and `Transport`. Call `raft.NewRaft(...)` which spawns background goroutines for processing logs, heartbeats, and leader elections.
  2. **Bootstrap**: If configuring a fresh cluster, `BootstrapCluster()` initializes a single-node configuration into the stable store.
  3. **Execution**: Clients submit commands via `Apply()`, returning an asynchronous `ApplyFuture`. The leader appends entries to its `LogStore`, replicates them via AppendEntries RPCs, commits them once a quorum acknowledges, applies them to the FSM, and responds to the client.
  4. **Termination**: Invoking `Shutdown()` gracefully cancels background loops, flushes state, closes transports and storage layers.

---

## 2. Core Mechanisms, Algorithms & Low-Level Techniques
- **Fundamental Invariants**: 
  - **Election Safety**: At most one leader can be elected per term.
  - **Leader Append-Only**: A leader never overwrites or truncates its own entries; it only appends new ones.
  - **Log Matching**: If two entries in different logs have the same index and term, then they store the same command.
  - **Leader Completeness**: If a log entry is committed in a given term, that entry will be present in the logs of the leaders for all higher-numbered terms.
  - **State Machine Safety**: If a server has applied a log entry at a given index to its state machine, no other server will ever apply a different log entry for the same index.
- **Subsystem Interfacing**:
  - Leverages Go channels and condition variables (`sync.Cond`) for synchronization within the core consensus loop (`raftNode` dispatcher).
  - Uses connection pooling in `net_transport.go` to maintain persistent bidirectional stream connections for multiplexed RPCs (AppendEntries, RequestVote, InstallSnapshot).
- **Security & Integrity Model**:
  - Stream framing with explicit magic bytes and RPC type prefixes to prevent protocol confusion attacks.
  - UUID-based server identities (`ServerID`) combined with network addresses (`ServerAddress`) to prevent stale node routing during dynamic cluster membership changes.

---

## 3. Data Contracts, Structs & Core API Signatures

```go
package raft

import (
	"io"
	"time"
)

type LogType uint8

const (
	LogCommand    LogType = iota
	LogNoop
	LogAddPeerDeprecated
	LogRemovePeerDeprecated
	LogConfiguration
)

type Log struct {
	Index      uint64
	Term       uint64
	Type       LogType
	Data       []byte
	Extensions []byte
	AppendedAt time.Time
}

type ApplyFuture interface {
	Error() error
	Response() interface{}
	Index() uint64
}

type FSM interface {
	Apply(*Log) interface{}
	Snapshot() (FSMSnapshot, error)
	Restore(io.ReadCloser) error
}

type FSMSnapshot interface {
	Persist(snapshot Sink) error
	Release()
}

type LogStore interface {
	FirstIndex() (uint64, error)
	LastIndex() (uint64, error)
	GetLog(index uint64, log *Log) error
	StoreLog(log *Log) error
	StoreLogs(logs []*Log) error
	DeleteRange(min, max uint64) error
}

type StableStore interface {
	Set(key []byte, val []byte) error
	Get(key []byte) ([]byte, error)
	SetUint64(key []byte, val uint64) error
	GetUint64(key []byte) (uint64, error)
}
```

---

## 4. Production-Ready Scaffolding Boilerplate (Copy-Paste)

```go
package main

import (
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"time"

	"github.com/hashicorp/raft"
	raftboltdb "github.com/hashicorp/raft-boltdb"
)

// SimpleFSM implements raft.FSM for an in-memory key-value store.
type SimpleFSM struct{}

func (f *SimpleFSM) Apply(l *raft.Log) interface{} {
	// Execute deterministic state machine mutations based on l.Data
	return nil
}

func (f *SimpleFSM) Snapshot() (raft.FSMSnapshot, error) {
	return &SimpleSnapshot{}, nil
}

func (f *SimpleFSM) Restore(rc io.ReadCloser) error {
	defer rc.Close()
	return nil
}

type SimpleSnapshot struct{}

func (s *SimpleSnapshot) Persist(sink raft.SnapshotSink) error {
	sink.Close()
	return nil
}

func (s *SimpleSnapshot) Release() {}

func InitializeRaftNode(nodeID, bindAddr, dataDir string) (*raft.Raft, error) {
	config := raft.DefaultConfig()
	config.LocalID = raft.ServerID(nodeID)

	// Setup Base Directories
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create data dir: %w", err)
	}

	// Setup Log and Stable Stores using BoltDB
	boltStore, err := raftboltdb.NewBoltStore(filepath.Join(dataDir, "raft.db"))
	if err != nil {
		return nil, fmt.Errorf("failed to create bolt store: %w", err)
	}

	// Cache logs to optimize reads
	logCache, err := raft.NewLogCache(boltStore, boltStore)
	if err != nil {
		return nil, fmt.Errorf("failed to create log cache: %w", err)
	}

	// Setup Snapshot Store
	snapshotStore, err := raft.NewFileSnapshotStore(dataDir, 2, os.Stderr)
	if err != nil {
		return nil, fmt.Errorf("failed to create snapshot store: %w", err)
	}

	// Setup Network Transport
	addr, err := net.ResolveTCPAddr("tcp", bindAddr)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve bind address: %w", err)
	}

	transport, err := raft.NewTCPTransport(bindAddr, addr, 3, 10*time.Second, os.Stderr)
	if err != nil {
		return nil, fmt.Errorf("failed to create TCP transport: %w", err)
	}

	// Instantiate Raft
	fsm := &SimpleFSM{}
	r, err := raft.NewRaft(config, fsm, logCache, boltStore, snapshotStore, transport)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize raft node: %w", err)
	}

	// Bootstrap cluster if single node deployment
	configuration := raft.Configuration{
		Servers: []raft.Server{
			{
		ID:      config.LocalID,
		Address: transport.LocalAddr(),
			},
		},
	}
	r.BootstrapCluster(configuration)

	return r, nil
}

func main() {
	node, err := InitializeRaftNode("node-1", "127.0.0.1:11000", "./raft-data")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Initialization error: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("Raft node initialized successfully. Current state:", node.State())
	
	// Keep process alive for demonstration purposes
	select {}
}
```

---

## 5. Engineering Invariants, Tradeoffs & Gotchas
- **Performance & Concurrency Characteristics**:
  - Write amplification is directly tied to underlying `LogStore` and `StableStore` fsync operations. High transaction throughput requires high-performance disk engines (e.g., BoltDB tuning, MDB).
  - Lock contention can occur on large clusters during mass AppendEntries processing; log caching (`LogCache`) mitigates disk reads for trailing followers.
- **Failure Modes & Edge Cases**:
  - **Split-Brain**: Prevented strictly via strict majority Quorum checks (`(N/2) + 1`) during elections and log commitments.
  - **Disk Full / Corruption**: If the stable store or log store fails to sync metadata (current term, voted for), node crash-loops or panics can occur. Proper filesystem monitoring is mandatory.
  - **Network Partitions**: Nodes isolated in a minority partition will step down or fail elections, remaining in candidate/follower states until connectivity recovers.
- **Hard Prerequisites**:
  - Go version 1.25+ toolchain.
  - Reliable POSIX-compliant filesystem semantics supporting synchronous writes (`fsync`) to guarantee durability invariants.