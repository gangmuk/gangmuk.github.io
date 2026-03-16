---
layout: post
title: "Performance benchmark for different server architecture"
date: 2025-07-22
---

### Thread-blocking approach
flask

flask with gunicorn


System Resources per Request:
```
Request 1 → Thread 1 (8MB stack) → BLOCKED waiting
Request 2 → Thread 2 (8MB stack) → BLOCKED waiting  
Request 3 → Thread 3 (8MB stack) → BLOCKED waiting
...
Request 1000 → Thread 1000 (8MB stack) → BLOCKED waiting
```
What happens at OS level:

1. Thread Creation: OS allocates 8MB stack per thread
2. Context Switching: CPU switches between threads (expensive)
3. Memory Usage: 1000 requests = 8GB just for thread stacks
4. Thread Blocking: Thread sleeps, waiting for completion_event.wait()

```
Memory: 10,000 × 8MB = 80GB
Threads: 10,000 OS threads
CPU: Constant context switching overhead
Limit: System crashes around 10,000-50,000 threads
```

### Event loop approach
fastapi
```
Request 1 → Event Loop → await future → SUSPENDED (no thread)
Request 2 → Event Loop → await future → SUSPENDED (no thread)
Request 3 → Event Loop → await future → SUSPENDED (no thread)
...
Request 1000 → Event Loop → await future → SUSPENDED (no thread)
```
What happens at OS level:

1. Single Thread: One event loop thread handles all requests
2. No Context Switching: No thread switching overhead
3. Memory Usage: ~100KB per suspended coroutine (vs 8MB per thread)
4. No Blocking: Requests are suspended, not blocked

```
Memory: 10,000 × 100KB = 1GB  
Threads: 1 OS thread
CPU: Minimal overhead
Limit: Can handle millions of concurrent requests
```