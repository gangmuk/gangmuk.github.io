---
layout: post
title: "Kubernetes Scalability"
tags: [k8s, scalability, etcd]
date: 2025-08-25
category: blog
---

# Kubernetes Scalability: From etcd Limitations to Kube-Brain Solutions

## Introduction

Kubernetes has become the de facto standard for container orchestration. I have not experienced scalability issue since I have used mostly tens of nodes in kubernetes. But during my internship at Bytedance, I heard that when it scales out to tens of thousands of nodes and hundreds of thousands of pods, it faces scalability issues. This post is a note of my understanding of how kubernetes achieves high scalability. 

What this post promises to you is
- explaining some part of Kubernetes design and why it is designed in such a way
- potential scalability bottlenecks in kubernetes (etcd)
- some existing solutions

What it does not have is
- implementation detail explanation of either K8S or other solutions
- performance numbers

## Understanding Kubernetes Architecture and State Management

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 CONTROL PLANE                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ kube-scheduler│    │controller-mgr│    │   kubectl    │    │  Other       │     │
│  │              │    │              │    │   (CLI)      │    │  Controllers │     │
│  │              │    │              │    │              │    │              │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │                   │             │
│         │ Watch/List        │ Watch/List        │ CRUD              │ Watch/List  │
│         │ (Pods to          │ (All Resources)   │ Operations        │ (Various    │
│         │  schedule)        │                   │                   │  Resources) │
│         │                   │                   │                   │             │
│         ▼                   ▼                   ▼                   ▼             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                        kube-apiserver                                       │  │
│  │                                                                             │  │
│  │  • Validates requests                                                       │  │
│  │  • Applies RBAC                                                            │  │
│  │  • Serializes/deserializes objects                                         │  │
│  │  • Manages watch streams                                                    │  │
│  │  • Coordinates with etcd                                                    │  │
│  └─────────────────────────┬───────────────────────────────────────────────────┘  │
│                            │                                                      │
│                            │ gRPC API                                             │
│                            │ (Read/Write/Watch)                                   │
│                            ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                          etcd Cluster                                       │  │
│  │                                                                             │  │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │  │
│  │   │etcd-node-1  │  │etcd-node-2  │  │etcd-node-3  │                        │  │
│  │   │   (Leader)  │  │ (Follower)  │  │ (Follower)  │                        │  │
│  │   └─────────────┘  └─────────────┘  └─────────────┘                        │  │
│  │            │              │              │                                  │  │
│  │            └──────────────┼──────────────┘                                  │  │
│  │                      Raft Consensus                                         │  │
│  │                                                                             │  │
│  │  • Stores ALL cluster state                                                │  │
│  │  • Provides strong consistency                                              │  │
│  │  • Single Raft group for entire keyspace                                   │  │
│  │  • Watch API for real-time notifications                                    │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### The Core Kubernetes Control Plane

At the heart of every Kubernetes cluster lies the **kube-apiserver**, which serves as the central nervous system for all cluster operations. Every interaction with the cluster—whether from kubectl commands, controller operations, or kubelet communications—flows through this single API endpoint.

The standard Kubernetes architecture follows this flow:

1. **Request Reception**: Users, controllers, and cluster components send requests to the kube-apiserver
2. **Validation and Processing**: The API server validates requests and applies business logic
3. **State Persistence**: All cluster state is written to etcd, a distributed key-value store
4. **Event Distribution**: Changes are propagated to watching clients through the watch API

### Client-Side Caching and the Shared Informer Pattern

To prevent overwhelming the API server with constant polling, Kubernetes implements a sophisticated client-side caching mechanism called the **shared informer pattern**:

**Initial Synchronization**: When a client (kubelet, controller, etc.) starts, it performs an initial `List` operation to retrieve the current state of resources it needs to monitor.

**Watch Mechanism**: After the initial sync, clients establish persistent `Watch` connections to receive real-time updates about resource changes. Each event includes a `resourceVersion` that acts as a consistency cursor.

**In-Memory Cache**: Clients maintain local caches of resources, updated in real-time through the watch stream.

**Event Handlers**: Custom logic triggers when resources are added, updated, or deleted, enabling reactive behavior without polling.

This pattern provides several critical benefits:
- **Reduced API Server Load**: Multiple clients share a single watch stream per resource type
- **Real-time Responsiveness**: Changes propagate instantly to interested clients  
- **Consistent State View**: Clients maintain eventually-consistent views of cluster state

### Why etcd Was Chosen: The Watch API and Consensus

etcd wasn't selected arbitrarily as Kubernetes' backing store. Two fundamental requirements drove this choice:

**Strong Consistency**: Kubernetes controllers make decisions based on cluster state. Inconsistent views could lead to catastrophic failures, such as scheduling pods to non-existent nodes or creating conflicting resource assignments. etcd's Raft consensus algorithm ensures all nodes have identical, synchronized data.

**The Watch API**: This is etcd's killer feature for Kubernetes. etcd provides a native watch mechanism that allows clients to subscribe to key changes and receive real-time event streams. This enables Kubernetes' reactive, event-driven architecture where controllers respond instantly to state changes rather than polling for updates.

Without these features, Kubernetes would be either unreliable (lacking consistency) or inefficient (requiring constant polling).

## The Scalability Limitation in etcd

### etcd's Architectural Bottlenecks

Despite client-side caching, etcd faces fundamental scalability limitations that become apparent at hyperscale:

**Single Raft Group Bottleneck**: All cluster data resides within a single etcd cluster managed by one Raft consensus group. Every write operation must be replicated to a majority of etcd nodes before being committed. This creates a sequential bottleneck that cannot be parallelized.

**Write Throughput Limitations**: As the number of objects and change frequency increases, the volume of write operations overwhelms etcd's ability to maintain consensus efficiently. Adding more etcd nodes beyond 5-7 members actually degrades performance due to increased consensus overhead.

**Watch Stream Overhead**: While caching reduces reads, maintaining thousands of concurrent watch streams for numerous resources creates significant overhead on both the API server and etcd cluster.

**Initial Synchronization Impact**: New clients must perform expensive `List` operations against large datasets. In clusters with hundreds of thousands of objects, these operations can severely impact etcd performance.

These limitations manifest as:
- Increased API server response times
- Watch event delays affecting controller reactivity  
- Cluster instability under high load
- Practical limits around 5,000-10,000 nodes per cluster

## Scalability Bottleneck

Before exploring solutions, let's clarify what etcd actually is by understanding the layered architecture of distributed storage systems.

### Understanding the Building Blocks

**Key-Value Store**: A data structure that maps keys to values, like a hash table. Simple operations: `put(key, value)`, `get(key)`, `delete(key)`. No complex queries, no joins—just fast key-based lookups. Examples: HashMap (in-memory), RocksDB (single-machine persistent).

**Replicated State Machine**: A technique for achieving fault tolerance. The idea: multiple servers maintain identical copies of the same state machine (e.g., a key-value store). They receive the same sequence of commands in the same order, so they all produce the same state. If one server fails, others continue serving requests. The challenge: ensuring all replicas agree on the order of operations.

**Consensus Algorithm**: Consensus algorithms solve the ordering problem in replicated state machines by ensuring all non-faulty replicas agree on a consistent sequence of operations, despite network delays, partitions, and crash failures. Raft elects a leader who proposes the order of operations; followers replicate the leader's log. An operation is committed once replicated to a majority of servers, guaranteeing it won't be lost even if the leader fails

**Distributed Key-Value Store**: A system that combines the above concepts—a key-value store replicated across multiple machines using consensus to ensure both fault tolerance and strong consistency. When you write to etcd, Raft ensures all replicas agree on the operation's order, then each replica applies it to its local KV store, producing identical state across all nodes. This is precisely what etcd is.

### The Relationship in etcd

etcd implements the **replicated state machine** using the Raft consensus algorithm, where the "state machine" being replicated is a key-value store.

```
┌─────────────────────────────────────────────────┐
│           etcd's Architecture                   │
├─────────────────────────────────────────────────┤
│  Consensus Layer (Raft)                         │
│  - Leader election, log replication             │
│  - Ensures all replicas see operations in       │
│    the same order                               │
│  - Output: totally-ordered log of operations    │
│                    ↓                            │
│  Application State Machine (KV Store)           │
│  - Deterministically applies operations from log│
│  - put(k,v), get(k), delete(k)                  │
│  - Output: consistent key-value state           │
└─────────────────────────────────────────────────┘

Result: All replicas execute the same operations in the same order,
        producing identical key-value state → Fault Tolerance
```

**The design question for scalability**: How do you organize consensus and state across multiple machines?

- **etcd's approach**: ONE Raft group manages the ENTIRE keyspace. Simple, strongly consistent, but fundamentally sequential.
- **Alternative approach (TiKV)**: MULTIPLE Raft groups, each managing a KEY RANGE. More complex, but enables parallel processing.

This design choice—the granularity at which you apply consensus—determines scalability limits. Solutions like Kube-Brain replace etcd with distributed systems that choose different consensus granularity.

However, simply saying "etcd is slow" oversimplifies the problem. To understand why replacing etcd helps and what exactly Kube-Brain and TiKV solve, we need to examine the specific design constraints that etcd operates under and why they become bottlenecks.

### Why etcd's Single Raft Group Architecture Limits Scalability

etcd was designed with a critical constraint: **all data must live in a single Raft consensus group**. This decision stems from etcd's core use case—storing critical cluster coordination state where strong consistency and linearizability are non-negotiable.

**Why this design?** A single Raft group provides the strongest consistency guarantees. Every write goes through one leader, which serializes all operations and ensures a global ordering of events. This makes reasoning about consistency trivial—there's never any ambiguity about which state is "correct" because there's only one authoritative source of truth. For small clusters (hundreds to low thousands of nodes), this provides rock-solid reliability with acceptable performance.

**The fundamental bottleneck:** The single-leader architecture means all write operations, regardless of which keys they affect, must be processed sequentially by one node. Even if you're updating completely independent keys (a pod in namespace A and a node status in the cluster), both writes must wait for their turn through the same leader. This is a **fundamental sequential bottleneck** that cannot be parallelized.

As cluster size grows, write volume grows proportionally:
- Node heartbeats (every node sends status updates every 10 seconds)
- Pod status updates (every pod lifecycle change)
- Endpoint updates (as services scale)
- Custom resource updates (from operators and controllers)

All of this write traffic converges on a single Raft leader that must:
1. Receive the write request
2. Append it to its log
3. Replicate to a majority of followers
4. Wait for acknowledgment
5. Apply to its state machine
6. Respond to the client

Only then can it process the next write. This sequential processing creates a hard throughput ceiling that no amount of vertical scaling can overcome.

### The Watch Stream Multiplication Problem

The second bottleneck is how etcd serves watch streams. When a client watches a key prefix (e.g., all pods), etcd must:
1. Track that watch registration in memory
2. For every write to keys under that prefix, match it against all active watches
3. Queue the event for delivery to each matching watcher
4. Handle flow control if watchers fall behind

At hyperscale, you might have:
- Hundreds of controllers each watching multiple resource types
- Thousands of kubelets each watching pods scheduled to them
- Multiple kube-apiserver instances, each maintaining watch streams from many clients

This creates a **watch stream amplification effect**: a single write to etcd might need to be delivered to hundreds or thousands of watch streams. While etcd handles this efficiently at moderate scale, it becomes a memory and CPU bottleneck when watch streams number in the thousands and write frequency is high.

### Why Kubernetes Can't Just "Shard" etcd

You might ask: why not run multiple etcd clusters, one per namespace or one per region? The problem is **cross-resource dependencies in Kubernetes' data model**.

The scheduler needs to see:
- All unscheduled pods (across all namespaces)
- All nodes (cluster-wide resource)
- All persistent volumes (cluster-wide resource)
- Various scheduling policies

Similarly, controllers often operate on resources across namespace boundaries. Sharding etcd would require either:
1. Cross-shard queries (destroying consistency guarantees)
2. Maintaining duplicate data across shards (creating consistency nightmares)
3. Restricting Kubernetes' data model (breaking existing applications)

This is why etcd's architecture—designed for correctness—becomes the bottleneck as Kubernetes scales. The solution isn't to make etcd faster, but to replace it with a storage system designed for horizontal scalability while preserving the consistency semantics Kubernetes requires.

### Design Space for Scalable Kubernetes Storage

Given the constraints we've identified, what design-level approaches could improve Kubernetes scalability? Let's examine the fundamental tradeoffs and solution categories.

#### Approach 1: Partition the Consensus Scope

**Core idea**: Instead of one consensus group for the entire keyspace, partition into multiple independent consensus groups based on key ranges.

**Design rationale**: Kubernetes writes to logically independent keys (node-1's heartbeat vs pod-1's status) have no causal dependencies. Forcing them through the same consensus protocol creates **false serialization**. Partitioning allows parallel consensus on independent key ranges.

**Example architecture**:
```
Single Consensus Group (etcd):
  ALL keys → ONE Raft group → ONE leader → Sequential writes

Multiple Consensus Groups (sharded approach):
  Key range [0x00, 0x10) → Raft group A → Leader A ┐
  Key range [0x10, 0x20) → Raft group B → Leader B ├→ Parallel writes
  Key range [0x20, 0x30) → Raft group C → Leader C ┘
```

**The scalability gain**: Write throughput scales with the number of partitions. Independent leaders process disjoint key ranges simultaneously, eliminating the single-leader bottleneck.

**The compatibility challenge**: Kubernetes assumes etcd's API, which presupposes a single consistent keyspace with global ordering. Partitioned storage requires:
- An **adaptation layer** that presents etcd's single-keyspace API while dispatching to multiple consensus groups underneath
- **Watch stream translation** from per-partition watches to global watch semantics
- **Cross-partition consistency** when Kubernetes operations span multiple key ranges

Real-world implementations: TiKV (multi-region Raft), CockroachDB (range-based replication). Systems like KubeWharf's Kube-Brain provide the adaptation layer.

#### Approach 2: Optimize the Watch Distribution Model

**Core idea**: Decouple watch event storage and distribution from the primary consensus path.

**Design rationale**: In etcd, the leader must both:
1. Achieve consensus on writes (necessary for correctness)
2. Notify all watchers of changes (expensive fan-out operation)

These concerns could be separated. The consensus layer commits writes; a separate **watch distribution layer** asynchronously propagates events to watchers.

**Potential architecture**:
```
Write path:  Client → Consensus → Commit (minimize latency)
Watch path:  Commit → Event Log → Watch Fanout → Clients (parallel distribution)
```

**The scalability gain**: Watch distribution can be horizontally scaled independently of consensus. Multiple watch servers read the committed log and serve different subsets of clients.

**The consistency tradeoff**: Introducing asynchrony between commits and watch notifications creates eventual consistency windows. Kubernetes controllers might see stale state briefly. This requires careful analysis of whether Kubernetes' reconciliation model can tolerate such delays.

#### Approach 3: Hierarchical Control Plane Architecture

**Core idea**: Instead of a flat cluster where all nodes connect to one control plane, introduce hierarchy—regional control planes with a lightweight coordination layer above.

**Design rationale**: Many Kubernetes operations are **locality-preserving**. Pods on rack A rarely need to coordinate with pods on rack B. Yet the flat architecture forces all state through the same global store. A hierarchical design could keep local operations local.

**Conceptual structure**:
```
Flat architecture (current):
  All kubelets → Single API server fleet → Single etcd

Hierarchical architecture:
  Kubelets (Region 1) → Regional API server → Regional storage
  Kubelets (Region 2) → Regional API server → Regional storage
             ↓                    ↓
        Global coordinator (minimal cross-region state)
```

**The scalability gain**: Regional control planes handle most traffic locally. The global layer only coordinates cross-region operations (scheduling decisions, global services).

**The operational complexity**: Now you have multiple control planes with complex failure modes. What happens when a regional control plane fails? How do you migrate pods between regions? This significantly complicates Kubernetes' operational model.

#### The Fundamental Tradeoff

All approaches face the same essential tension:

**Kubernetes' original design**:
- Strong consistency (all components see the same state)
- Global visibility (controllers can watch anything)
- Simple mental model (one source of truth)
- **Cost**: Sequential bottleneck at moderate scale

**Scalability-oriented designs**:
- Partitioned consensus or eventual consistency
- Limited visibility (regional or namespace-scoped)
- Complex mental model (multiple coordination domains)
- **Benefit**: Horizontal scalability to massive scale

There's no free lunch. Improving scalability requires **either** relaxing consistency guarantees **or** partitioning visibility **or** accepting significant operational complexity. The choice depends on whether your use case can tolerate these tradeoffs.

### Implications for Kubernetes Evolution

The Kubernetes community has largely accepted that pushing beyond ~5,000-10,000 nodes requires fundamental architectural changes, not incremental optimizations. Organizations operating at hyperscale (tens of thousands of nodes) typically choose one of:

1. **Multi-cluster architectures**: Run many independent Kubernetes clusters with cross-cluster coordination at the application layer
2. **Storage layer replacement**: Keep Kubernetes' API unchanged but replace etcd with partitioned storage (requires compatibility layers)
3. **Fork and customize**: Modify Kubernetes itself to introduce hierarchy or relaxed consistency

Each represents a different point in the design space we outlined above. The "right" choice depends on your scale requirements, operational constraints, and tolerance for diverging from standard Kubernetes.