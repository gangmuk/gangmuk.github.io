---
layout: post
title: "Deploying modified server without build, push, pull, and restart"
tags: [flask, k8s]
date: 2025-06-14
---

# Deploying modified server without build,push,pull, and restart

## The Daily Development Nightmare

A part of my project code is running flask server and it is deployed on Kubernetes. And over the engineering, you encounter bug, fix, add new feature, refactor, etc. Let's say you need to add a single debug statement to see what's happening. In a local environment, this would take 5 seconds—save file, see output. But in Kubernetes? Well, at least 30 seconds up to minutes (sometimes tens of minutes).

The workflow goes like this: **edit code, build Docker image, push to registry (seconds to minutes depending on your internet), restart related deployment(pods), and wait for rollout**. By the time you see your debug output, you've forgotten what you were investigating. You've checked Slack, browsed Reddit, maybe started a completely different task. The **context switch overhead is devastating**.

This isn't just about waiting—it's about how the wait destroys your ability to think about problems iteratively. Debugging becomes a batch process instead of an interactive exploration. You start making larger, riskier changes because the cost of iteration is so high. Your **development velocity plummets**.

---

# Fix
## first trial

I simply tried to kill the flask server process and execute the python command again. 
But there was a fundamental problem. the Flask process was PID 1 in the container.

```Dockerfile
CMD ["python", "routing_agent_service.py"]
```

If I do this in Dockerfile, this process becomes PID 1.

In Docker containers, PID 1 is special. When PID 1 exits, the entire container terminates immediately. 

The Breakthrough: Separating Concerns

## working solution
Make Flask not PID 1.

Create a lightweight wrapper script that becomes PID 1 and manages the Flask process as a child. The wrapper's only job is process lifecycle management—starting Flask, restarting it on demand, and handling container shutdown signals.

Bash

# start.sh becomes PID 1

```bash
#!/bin/bash
# start.sh - Simple wrapper that keeps running even if Flask dies

echo "Starting Flask app wrapper..."
echo "Wrapper PID: $$"

# Function to handle signals
cleanup() {
    echo "Received signal, shutting down..."
    if [ ! -z "$FLASK_PID" ]; then
        echo "Killing Flask PID: $FLASK_PID"
        kill -TERM $FLASK_PID 2>/dev/null
        wait $FLASK_PID 2>/dev/null
    fi
    echo "Wrapper exiting"
    exit 0
}

# Function to restart Flask
restart_flask() {
    echo "Restarting Flask..."
    if [ ! -z "$FLASK_PID" ]; then
        echo "Stopping current Flask PID: $FLASK_PID"
        kill -TERM $FLASK_PID 2>/dev/null
        wait $FLASK_PID 2>/dev/null
    fi
    start_flask
}

# Function to start Flask
start_flask() {
    echo "Starting Flask application..."
    cd /app
    python routing_agent_service.py &
    FLASK_PID=$!
    echo "Flask started with PID: $FLASK_PID"
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT
trap restart_flask SIGUSR1

mkdir -p /app/logs

start_flask
while true; do
    if ! kill -0 $FLASK_PID 2>/dev/null; then
        echo "Flask process died, restarting..."
        start_flask
    fi
    if [ -f "/app/.restart_trigger" ]; then
        echo "Found restart trigger file, restarting Flask..."
        rm -f /app/.restart_trigger
        restart_flask
    fi
    sleep 5
doneR1
```

and Dockerfile should execute this wrapper process not python directly.

```Dockerfile
CMD ["/app/start.sh"]
```

This architecture lets PID 1 never exit: The wrapper script runs indefinitely, so the container never terminates unexpectedly.
Clean restart semantics: Killing and restarting Flask is straightforward process management.
Fresh code loading: A new Python process loads all updated modules from scratch.


## User(me) experience
The implementation was surprisingly minimal. The wrapper script is about 30 lines of bash. The Dockerfile change was a single line. 

But the real impact was psychological! When iteration is fast, you debug fast, more productively, and even your debugging fashion(style and pattern) could be changed. You're willing to add temporary logging, test edge cases, try experimental fixes. You can move more easily to do 'test and see' instead of 'should I do this or that?' since the overhead of updating the code becomes smaller. Productivity-wise, you stay in the zone instead of constantly context switching. Problems that seemed complex often turned out to be simple once you could explore them iteratively.

For most of people who have reliable and fast internet connection, this might not be interesting. But if not, well, code shipping for remote container can be really annoying and ruin your day.

It also highlighted how much development velocity depends on feedback loop timing. There's a qualitative difference between 30-second and 15-minute iterations. It's not just 30x faster—it changes how you think about problems. Fast feedback enables more focus, a more exploratory, experimental development style that often leads to better solutions.