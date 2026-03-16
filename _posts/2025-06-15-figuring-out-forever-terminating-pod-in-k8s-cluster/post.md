---
layout: post
title: "Debugging Forever Terminating Pods in Kubernetes"
date: 2025-06-15
tags: [k8s, debugging, failure, disk pressure]
category: blog
---

# Debugging Forever Terminating Pods in Kubernetes

*Tracking down why a pod was stuck in "Terminating" state for 10+ hours.*

## The Issue

One of our LLaMA model pods had been stuck in `Terminating` state for over 10 hours. When we tried to delete it manually, the command hung forever:

```bash
$ kubectl get pods
NAME                                    READY   STATUS        RESTARTS   AGE
llama-3-8b-instruct-785975c76d-psqzk    2/2     Terminating   0          30d

$ kubectl delete pod llama-3-8b-instruct-785975c76d-psqzk
pod "llama-3-8b-instruct-785975c76d-psqzk" deleted
# ^ This command hangs here forever and never completes
```

The delete command appeared to accept the request but never finished executing.

## Pod Description

First, we examined the pod itself:

```bash
$ kubectl describe pod llama-3-8b-instruct-785975c76d-psqzk
```

Key observations from the pod description:
```bash
Name:                      llama-3-8b-instruct-785975c76d-psqzk
Namespace:                 default
Node:                      10.0.1.14/10.0.1.14
Start Time:                Wed, 14 May 2025 20:40:45 -0700
Status:                    Terminating (lasts 10h)
Termination Grace Period:  60s
IP:                        10.0.1.83
Controlled By:  ReplicaSet/llama-3-8b-instruct-785975c76d

Conditions:
  Type               Status
  Initialized        True
  Ready              False
  ContainersReady    True
  PodScheduled       True
  DisruptionTarget   True

Events:                      <none>
```

Notable details:
- **Status**: `Terminating (lasts 10h)` - stuck for an unusually long time
- **Node**: `10.0.1.14` - we'd need to investigate this node
- **Conditions**: `Ready: False` but `ContainersReady: True` - containers were running fine
- **Events**: `<none>` - no recent events explaining the termination
- **Termination Grace Period**: Only 60 seconds, but it had been terminating for 10 hours

The pod itself looked healthy except for being stuck in termination. The containers were running normally, and there were no error events.

## Checking Standard Resources

**Persistent Volumes:**
```bash
$ kubectl get pv,pvc
# Only found unrelated storage - no volume mount issues
```

**Recent Events:**
```bash
$ kubectl get events --sort-by=.metadata.creationTimestamp
LAST SEEN   TYPE      REASON                  OBJECT                                        MESSAGE
2m23s       Normal    EnsuringLoadBalancer    service/deepseek-llm-7b-chat                  Ensuring load balancer
19m         Warning   FailedScheduling        pod/vllm-v6d-stability-test-79nvk             0/19 nodes are available: 1 node(s) had untolerated taint {node.kubernetes.io/unreachable: }, 15 node(s) didn't match pod affinity rules...
21m         Warning   FailedScheduling        pod/llama-3-8b-instruct-785975c76d-52btv      0/19 nodes are available: 1 node(s) had untolerated taint {node.kubernetes.io/unreachable: }, 3 node(s) had untolerated taint {vci.vke.volcengine.com/node-type: vci}, 7 Insufficient nvidia.com/gpu...
21m         Normal    Scheduled               pod/llama-3-8b-instruct-785975c76d-52btv      Successfully assigned default/llama-3-8b-instruct-785975c76d-52btv to 10.0.1.7
```

The events revealed something interesting:
- **Multiple pods failing to schedule** due to `node.kubernetes.io/unreachable` taint
- **A new pod** `llama-3-8b-instruct-785975c76d-52btv` was created and scheduled to node `10.0.1.7`
- **The ReplicaSet had created a replacement** - but our original pod was still stuck

This suggested that Kubernetes had detected an issue with a node and was trying to reschedule workloads, but our original pod was still stuck.

## Node Investigation

We examined the node where the pod was running:

```bash
$ kubectl describe node 10.0.1.14
```

This command revealed the root cause:

```yaml
Taints:             node.kubernetes.io/unreachable:NoExecute
                    node.kubernetes.io/unreachable:NoSchedule

Conditions:
  Ready                       Unknown
  MemoryPressure              Unknown  
  DiskPressure                Unknown
  PIDPressure                 Unknown
```

All conditions showed `Unknown` status with the message: **"Kubelet stopped posting node status"**

## Node Timeline and Kubernetes Response

Node conditions revealed a precise timeline:

- **01:14:35**: All health checks passing (`ChronydIsHealthy`, `KubeletIsHealthy`, etc.)
- **01:15:14**: Last successful heartbeat from kubelet
- **01:18:01**: Communication completely lost - all conditions became `Unknown`

The node went from completely healthy to completely unreachable in 3 minutes. This was a sudden, catastrophic failure.

**Kubernetes Response to Node Failure:**

1. **Node Controller Detection**: After missing several heartbeats (typically 40s), the node controller marked the node as `Unknown`
2. **Taint Application**: Kubernetes automatically applied `node.kubernetes.io/unreachable:NoExecute` taint
3. **Pod Eviction Trigger**: The taint triggered pod eviction from the unreachable node
4. **Graceful Termination Attempt**: Kubernetes sent SIGTERM to containers with a 60-second grace period
5. **ReplicaSet Response**: The ReplicaSet detected a missing pod and created a replacement on a healthy node
6. **Stuck Termination**: Since the node couldn't respond, the pod never acknowledged termination

This explains why our `kubectl delete` command hung - Kubernetes was waiting for the kubelet on the unreachable node to confirm the pod deletion.

## Confirming the Diagnosis

A simple node status check confirmed our theory:

```bash
$ kubectl get nodes
NAME        STATUS     ROLES    AGE   VERSION
10.0.1.14   NotReady   <none>   92d   v1.28.3-vke.16
# ... other nodes all showing Ready
```

Node `10.0.1.14` was the only `NotReady` node in the entire cluster.

## Understanding the Root Cause

**What happened:**
1. The underlying VM/instance hosting node `10.0.1.14` suffered a sudden infrastructure failure
2. This could be network connectivity loss, hardware failure, or hypervisor issues
3. The kubelet could no longer communicate with the Kubernetes API server
4. Kubernetes marked the node as unreachable and tried to gracefully terminate pods
5. Since the node couldn't respond, the pod got stuck in `Terminating` state
6. The ReplicaSet had already created a replacement pod on a healthy node

**Why this wasn't obvious initially:**
- The pod description showed healthy containers
- No resource pressure indicators
- No obvious error messages
- The events log didn't contain relevant information about this specific pod

## Why kubectl delete Hangs Forever

When we tried to delete the pod manually, the command hung indefinitely:

```bash
$ kubectl delete pod llama-3-8b-instruct-785975c76d-psqzk
pod "llama-3-8b-instruct-785975c76d-psqzk" deleted
# ^ Command appears to succeed but hangs here forever
```

**Why this happens:**

1. **API Server Accepts Request**: The API server receives and accepts the delete request
2. **Graceful Deletion Process**: Kubernetes starts the graceful deletion workflow
3. **Waiting for Kubelet**: The API server waits for the kubelet on node `10.0.1.14` to confirm pod deletion
4. **Unreachable Node**: Since the node is unreachable, the kubelet never responds
5. **Infinite Wait**: The command hangs forever waiting for confirmation that will never come

This is Kubernetes' safety mechanism - it won't remove a pod from the API server until it's certain the pod has actually stopped running on the node.

## The Only Solution: Force Delete

Since the node couldn't respond, the only way to clean up the stuck pod was to force delete it:

```bash
$ kubectl delete pod llama-3-8b-instruct-785975c76d-psqzk --force --grace-period=0
pod "llama-3-8b-instruct-785975c76d-psqzk" force deleted
```

The `--force --grace-period=0` flags tell Kubernetes:
- Skip waiting for graceful termination
- Remove the pod from the API server immediately
- Don't wait for kubelet confirmation

This is safe when you've confirmed the node is truly unreachable, as there's no risk of the pod still running.



## Conclusion

What initially appeared to be a simple stuck pod revealed a complex chain of infrastructure failure and Kubernetes safety mechanisms. The detective work showed us that:

1. **The pod wasn't the problem** - it was a symptom of node failure
2. **Normal deletion commands fail** when nodes are unreachable due to Kubernetes' safety mechanisms
3. **Force deletion is the only solution** but should only be used after confirming the node is truly unreachable
4. **Kubernetes handled the situation correctly** by automatically creating replacement pods on healthy nodes

The key insight was understanding why the `kubectl delete` command hung forever - Kubernetes was protecting us from accidentally deleting a pod that might still be running by waiting for confirmation from an unreachable node. Once we understood this mechanism, the force delete approach became the clear and safe solution.

The next time you encounter a pod stuck in `Terminating` state, remember to investigate the underlying node health before attempting any fixes. The pod might just be the messenger telling you about a deeper infrastructure issue.