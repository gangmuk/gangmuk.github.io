# Kubernetes Scalability: From etcd Limitations to Kube-Brain Solutions

## Introduction

Kubernetes has become the de facto standard for container orchestration, but as organizations scale to hyperscale environments with tens of thousands of nodes and hundreds of thousands of pods, fundamental architectural limitations emerge. This comprehensive guide explores how Kubernetes manages state, why traditional architectures hit scalability walls, and how innovative solutions like Kube-Brain are reshaping the future of large-scale Kubernetes deployments.

## Part I: Understanding Kubernetes Architecture and State Management

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

## Part II: The Scalability Limitation (etcd)

### etcd's Architectural Bottlenecks

Despite client-side caching, etcd faces fundamental scalability limitations that become apparent at hyperscale:

**Single Raft Group Bottleneck**: All cluster data resides within a single etcd cluster managed by one Raft consensus group. Every write operation must be replicated to a majority of etcd nodes before being committed. This creates a sequential bottleneck that cannot be parallelized.

**Write Throughput Limitations**: As the number of objects and change frequency increases, the volume of write operations overwhelms etcd's ability to maintain consensus efficiently. Adding more etcd nodes beyond 5-7 members actually degrades performance due to increased consensus overhead.

**Watch Stream Overhead**: While caching reduces reads, maintaining thousands of concurrent watch streams for numerous resources creates significant overhead on both the API server and etcd cluster.

**Initial Synchronization Impact**: New clients must perform expensive `List` operations against large datasets. In clusters with hundreds of thousands of objects, these operations can severely impact etcd performance.

### Real-World Impact

These limitations manifest as:
- Increased API server response times
- Watch event delays affecting controller reactivity  
- Cluster instability under high load
- Practical limits around 5,000-10,000 nodes per cluster

## Part III: Some trials for more scalable k8s (replacing etcd!)

I found kube-brain project that aims to replace etcd with a more scalable solution.

### Kube-Brain

Kube-Brain, a part of KubeWharf, tries to solve the scalability problem of etcd. Etcd is scalable until a few thousand nodes. Okay, so what about just creating multiple clusters and each will be able to handle the scale with the current etcd. But what if you want a single k8s cluster for easier managment and you have tens of thousands of nodes in your cluster. Then, etcd will be a bottleneck. Kube-Brain aims to replace etcd.

### Kube-Brain Architecture

**Stateless Proxy Layer**: Kube-Brain itself is completely stateless, acting as an intelligent proxy between the kube-apiserver and a high-performance distributed storage backend.

**etcd API Compatibility**: Kube-Brain implements the exact same gRPC interface that kube-apiserver expects from etcd, including the critical watch API functionality. This ensures zero changes are required to existing Kubernetes code.

**Pluggable Storage Backend**: The actual data storage is delegated to a separate, horizontally scalable distributed database system designed for high throughput and massive scale.

### How Kube-Brain Achieves Scalability

**Horizontal Scaling of Proxy Layer**: Since Kube-Brain instances are stateless, they can be horizontally scaled behind a load balancer. Multiple API servers can connect to different Kube-Brain instances, distributing the request load.

**Backend Optimization**: Kube-Brain can leverage storage backends specifically optimized for Kubernetes' metadata access patterns (dominated by List and Watch operations rather than random key lookups).

**Decoupled Architecture**: By separating the API compatibility layer from the storage implementation, Kube-Brain allows the use of storage systems that would be impossible to integrate directly with Kubernetes.

### Standard vs. Kube-Brain Architecture

```
Standard Kubernetes:
kube-apiserver ──→ etcd (single Raft group)

Kube-Brain Architecture:  
kube-apiserver ──→ Kube-Brain (stateless proxy) ──→ Distributed Storage Backend
```

## Part IV: More performant distributed key-value store (TiKV)

Etcd's scalability is limited by its single Raft group architecture, which creates a bottleneck as the cluster size increases. There are other more performant distributed key-value stores like TiKV. Let's see how TiKV is different from etcd, how it scales better and why k8s can't simply use TiKV but sort of forced to stick to etcd.

### Why Standard Kubernetes Cannot Use TiKV Directly

The kube-apiserver is hard-coded to communicate with etcd's specific API, including its consistency model and watch mechanisms. There's no pluggable storage interface that would allow direct integration with other databases like TiKV.

Even if such an interface existed, TiKV and similar distributed stores don't natively provide etcd's watch API semantics that Kubernetes depends on for its reactive architecture.

### TiKV's Architectural Advantages

**Sharded Raft Architecture**: Unlike etcd's single Raft group, TiKV automatically partitions data into smaller regions, each managed by its own independent Raft group with dedicated leaders and followers.

**Parallel Consensus**: Multiple write operations can be processed concurrently across different regions, each handled by different leaders. This parallelism eliminates the single-leader bottleneck that constrains etcd.

**Linear Scalability**: Adding more nodes increases both storage capacity and throughput almost linearly, as new nodes can host additional regions and participate in parallel consensus operations.

**Massive Scale Support**: TiKV is designed to handle petabytes of data across thousands of nodes, far exceeding etcd's typical few-gigabyte limitations.

### Comparison: etcd vs. TiKV

| Feature | etcd | TiKV |
|---------|------|------|
| **Consensus Model** | Single Raft group for entire dataset | Sharded Raft groups per region |
| **Write Scalability** | Limited by single leader | Parallel processing across regions |
| **Storage Capacity** | ~2GB recommended maximum | Petabyte-scale capable |
| **Node Scaling** | 3-7 nodes optimal | Thousands of nodes supported |
| **Use Case** | Small, critical metadata | Large-scale, high-throughput applications |

### Why Distributed KV Stores Scale Better

The key insight is in the consensus distribution:

**etcd**: All data changes must go through a single Raft leader, creating a sequential bottleneck regardless of cluster size.

**TiKV**: Data is automatically sharded across multiple regions, each with its own Raft leader. Write operations to different regions can be processed in parallel, allowing throughput to scale with the number of regions.

This architectural difference enables TiKV to achieve linear scalability—adding more nodes directly increases the system's ability to handle concurrent operations.


### Seamless Integration into Kubernetes

Kube-Brain solves the integration challenge by providing perfect API compatibility:

1. **Translation Layer**: Kube-Brain translates etcd API calls into the appropriate protocol for its storage backend
2. **Watch API Implementation**: Complex logic maintains etcd-compatible watch streams backed by the distributed storage system
3. **Consistency Guarantees**: Ensures that the same consistency semantics expected by Kubernetes controllers are preserved

### Deployment Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│   kube-apiserver│────│  Kube-Brain     │────│  TiKV Cluster    │
│                 │    │  (Stateless     │    │  (Sharded        │
│                 │    │   Proxy)        │    │   Storage)       │
└─────────────────┘    └─────────────────┘    └──────────────────┘
                              │
                       ┌─────────────────┐
                       │  Load Balancer  │
                       │  (Multiple      │
                       │   Instances)    │
                       └─────────────────┘
```

In summary performance gain comes from...

**Request Distribution**: Multiple Kube-Brain instances can handle concurrent requests from multiple API servers, eliminating the single-endpoint bottleneck.

**Backend Optimization**: TiKV's sharded architecture allows write operations to be processed in parallel across multiple regions simultaneously.

**Read Scalability**: Both the proxy layer and storage backend can scale reads independently, supporting massive numbers of concurrent watch streams and list operations.

## Conclusion

Kubernetes' current architecture, built around etcd's strong consistency and watch API, has enabled the container orchestration revolution. However, the single-cluster, single-Raft-group model hits fundamental scalability walls at hyperscale.

Kube-Brain represents an innovative architectural approach that preserves Kubernetes' operational model while unlocking the scalability potential of modern distributed storage systems like TiKV. By providing a stateless proxy layer that maintains perfect etcd API compatibility while leveraging horizontally scalable storage backends, Kube-Brain enables Kubernetes to scale far beyond its traditional limitations.

This architectural evolution is crucial for organizations operating at hyperscale, where traditional Kubernetes clusters become bottlenecked by etcd's inherent design constraints. As the cloud-native ecosystem continues to mature, solutions like Kube-Brain will become increasingly important for unlocking the next generation of large-scale, distributed applications.

The future of Kubernetes scalability lies not in replacing its proven architectural patterns, but in evolving the underlying storage layer to match the scale demands of modern cloud-native workloads.