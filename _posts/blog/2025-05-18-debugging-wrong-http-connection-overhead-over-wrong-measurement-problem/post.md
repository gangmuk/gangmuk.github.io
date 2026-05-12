---
layout: post
title: "Debugging HTTP Connection Overhead"
tags: [failure, performance debugging, gateway, aibrix]
date: 2025-05-18
category: blog
---

This is basically a journal about a stupid debugging experience on microservice-applications on K8S.

I wrote this post to log how stupid the performance debugging can be...

## TLDR; 
I was doing performance debugging on AIBrix gateway and my request routing agent service. I added timing code and it showed ~500ms "connection" time. But the number was bogus from completely wrong measurement. I used `net.DialTimeout` (it dials a fresh TCP connection and returns a raw `net.Conn`) when measuring the http connection overhead. But `net.DialTimeout` does not use `http.Client`’s connection pool. Instead, it creates a separate http connection outside `http.Client`’s pool. The wrong measurement made me spend lots of hours trying to optimize the connection overhead which was NOT a problem at all. The lesson is *make sure that you are measuring the right thing in a right way.*. Yes, it is such an obivous thing but it is not easy! After instrumenting the real request path with `httptrace`, the connection time was ~0ms—connection reuse was fine; the measurement method was wrong.

## What happened
I have been working on LLM inference routing project. I have been modifying AIBrix gateway and implement a new request routing agent service for my research project. 
The existing AIBrix gateway (envoy proxy) will invoke my routing agent service with HTTP call. AIBrix gateway and routing agent service are running in aibrix k8s infrastructure as individual application in each pod. 

It adds more logics on the request critical path to run more complex request routing logic and also there is additional http call between gateway and request routing agent service. The early implementation was not optimized at all and had lots of inefficient codes. It was showing high latency in processing the routing logic. To find where the overhead is, I printed times in each critical section. 

First, I needed to check if it is caused by HTTP connection overhead or the routing agent service's routing logic computation has high overhead. It is serving infrastructure, so there will be multiple concurrent requests submitted to the system. It needs to process(making routing decision) them with low overhead. And based on my logging, it was showing high latency (~500ms) during http connection between AIBrix gateway and routing agent service. And I spent quite a lot of times on trying to reduce http connection overhead. But it was not the root cause... My measurement (time logging) was wrong.

This is what I was measuring. I was trying to measure as detailed as possible. From DNS resolution to connection establishment to request sending to response receiving.

```go
func SendRequestWithTiming(...) ([]byte, TimingResult, error) {
    var result TimingResult
    parsedURL, _ := url.Parse(url)
    hostName := parsedURL.Hostname()
    // Measurement 1: DNS Resolution
    dnsStart := time.Now()
    hosts, dnsErr := net.LookupHost(hostName)
    result.DNSTime = time.Since(dnsStart)
    // Measurement 2: Connection Test - THE PROBLEMATIC PART
    result.ConnectionTime = 0
    if len(hosts) > 0 {
        connStart := time.Now()
        port := "80"
        if strings.HasPrefix(url, "https://") {
            port = "443"
        }
        // Wrong measurement root cause. This creates a new TCP connection which is separate from the connection pool
        conn, dialErr := net.DialTimeout("tcp", hosts[0]+":"+port, timeout/2)
        result.ConnectionTime = time.Since(connStart)
        if dialErr != nil {
            log.Printf("Connection test failed: %v", dialErr)
        } else if conn != nil {
            conn.Close()  // Immediately close this test connection
        }
    }
    // 3. Actual HTTP request. It uses connection pool, meaning it will reuse the existing connection. When reusing the existing connection, there is no overhead.
    req, reqErr := http.NewRequest(method, url, bytes.NewBuffer(reqBody))
    if reqErr != nil {
        return nil, result, reqErr
    }
    for key, value := range headers {
        req.Header.Set(key, value)
    }
    reqStart := time.Now()
    resp, err := client.Do(req)
    result.RequestTime = time.Since(reqStart)
    ...

When I was sending requests, this is what I saw:

```
I0514 09:09:32.662052       1 latency_prediction_based.go:620] requestID: 132 -  Timing breakdown took, DNS: 4ms, Conn: 500ms, Req: 0ms, Send: 31ms, Read: 0ms, Parse: 0ms, Total: 536ms
```

With both services running in the same Kubernetes cluster and all k8s nodes are in the same rack, 500ms connection overhead is definitely excessive and not normal. The problem must be in the software stack.

## What I Was Actually Measuring (And Why It Was Wrong)

What `net.DialTimeout()` actually does at line 45 is ...
```go
conn, dialErr := net.DialTimeout("tcp", hosts[0]+":"+port, timeout/2)
```
1. DNS resolution (if needed)
2. TCP 3-way handshake (SYN → SYN-ACK → ACK)
3. Returns a raw TCP connection (`net.Conn`)
4. **Critical**: This connection is NOT in `http.Client`'s connection pool

This creates a **brand new TCP connection every single time** I measure. For HTTPS endpoints, add another 200-300ms for TLS handshake on top. Total: 200-500ms.

However, on line 66, when I call `client.Do(req)`, the `http.Client` uses a completely different connection from its connection pool. If connection pooling is working (which it was), `http.Client` reuses an existing connection with zero overhead.

**So what was I measuring?**
- Creating a throwaway connection just for timing → 500ms overhead
- Using a pooled connection for the actual request → 0ms overhead

I was measuring Connection A while optimizing for Connection B. They're not the same connection!

**What I should have done**: Use `net/http/httptrace.ClientTrace` to instrument the actual connection that `client.Do()` uses:

```go
trace := &httptrace.ClientTrace{
    GotConn: func(info httptrace.GotConnInfo) {
        // info.Reused tells you if connection was from the pool
        // true = 0ms overhead, false = new connection created
        result.ConnectionReused = info.Reused
        result.IdleTime = info.IdleTime
    },
    ConnectStart: func(network, addr string) {
        connectStart = time.Now()
    },
    ConnectDone: func(network, addr string, err error) {
        result.ConnectionTime = time.Since(connectStart)
    },
}
req = req.WithContext(httptrace.WithClientTrace(req.Context(), trace))
```

Simply, this is how to get the timing of the http connections used by the http client.

It looks very obvious but it was not because (obviousuly) I was using LLM to write time logging code saying "I want to measure detailed overhead including connection, request sending overhead ....".  (Shamelessly), I didn't read the code thoroughly and when I took a glimpse of it, the code made sense unless you understand what `net.DialTimeout()` actually does. Additionally, it was successfully built and shows the number. So, this is how stupid performance debugging that didn't exist started.
(I used Claude 3.5 Sonnet)

Later part of the post is detailed story about how I did performance debugging and optimization for non-existent problem. It is more about sharing the lessons learned.


## What happened next
I pasted my code and logs to the AI, asking, "I want to first understand what connection overhead is and how to solve it."

The AI assistant explained connection overhead in detail—the time needed for TCP handshakes, TLS negotiation, and session establishment. It confidently analyzed my code and suggested several improvements to my HTTP transport configuration:

- Increasing `MaxIdleConns` and `MaxIdleConnsPerHost`
- Extending `IdleConnTimeout`
- Implementing a more aggressive connection warmup strategy

But most critically, the AI endorsed and expanded upon my existing measurement, which used this function:

```go
func SendRequestWithTiming(
    client *http.Client,
    url string,
    method string,
    reqBody []byte,
    headers map[string]string,
    requestID string,
    timeout time.Duration,
) ([]byte, TimingResult, error) {
    // ... other code ...

    // 1. DNS Resolution
    dnsStart := time.Now()
    hosts, dnsErr := net.LookupHost(hostName)
    result.DNSTime = time.Since(dnsStart)

    // 2. Connection Test - THIS IS THE PROBLEMATIC PART
    result.ConnectionTime = 0
    if len(hosts) > 0 {
        connStart := time.Now()
        // Extract port if included in URL
        port := "80"
        if strings.HasPrefix(url, "https://") {
            port = "443"
        }
        // ... port extraction logic ...

        conn, dialErr := net.DialTimeout("tcp", hosts[0]+":"+port, timeout/2)
        result.ConnectionTime = time.Since(connStart)

        if dialErr != nil {
            // Log error
        } else if conn != nil {
            conn.Close()
        }
    }

    // ... HTTP request code ...
}
```

The AI analyzed this code and even suggested enhancements, adding instrumentation to check if connections were being reused. I implemented these changes, but the problem persisted—we were still seeing 500ms connection times, even with `ConnReuse: true` in the logs.

## The Rabbit Hole Got Deeper

Over several days, I spent hours implementing the AI's suggestions:

1. Modified the connection pool settings
2. Implemented more aggressive warmup strategies
3. Added detailed logging
4. Increased timeouts
5. Experimented with HTTP/2 vs HTTP/1.1

Each time, I returned to the AI with my results, and each time it offered new theories and more sophisticated approaches. We discussed:

- Network path analysis
- Connection pipelining
- DNS caching
- Server-side TCP settings

The AI's suggestions became increasingly complex, requiring significant code changes. I was spending more and more time chasing a performance issue that seemed stubborn and mysterious.

## How it was supposed to be measured

I was supposed to use Go's `httptrace` package to measure the right http connection overhead.

```go
func SendRequestWithTiming(...)
    ...
    var dnsStart, dnsEnd, connectStart, connectEnd, tlsStart, tlsEnd time.Time
    
    // Create HTTP request
    req, reqErr := http.NewRequest(method, url, bytes.NewBuffer(reqBody))
    
    // Set up HTTP tracing
    trace := &httptrace.ClientTrace{
        DNSStart: func(info httptrace.DNSStartInfo) {
            dnsStart = time.Now()
            // Log DNS start
        },
        DNSDone: func(info httptrace.DNSDoneInfo) {
            dnsEnd = time.Now()
            // Log DNS completion
        },
        ConnectStart: func(network, addr string) {
            connectStart = time.Now()
            // Log connection start
        },
        ConnectDone: func(network, addr string, err error) {
            connectEnd = time.Now()
            // Log connection completion
        },
        GotConn: func(info httptrace.GotConnInfo) {
            // Log connection details
            result.ConnectionReused = info.Reused
        },
        // More trace points...
    }
    ...
}
```

```
I0514 18:45:12.882154       1 latency_prediction_based.go:646] requestID: 451 -  Timing breakdown took, DNS: 0ms, Conn: 0ms, ConnReuse: true, Req: 0ms, Send: 18ms, Read: 2ms, Parse: 0ms, Total: 21ms
```

Connection time: **0ms**. The 500ms overhead just disappeared beacuse 500ms connection overhead never existed in the first place.