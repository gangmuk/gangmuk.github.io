---
layout: post
title: "How low disks space breaks envoy wasm cache and eventually makes http request routing fail (AIBrix LLM inference infra)"
tags: [failure, debugging, k8s, aibrix, envoy, wasm]
date: 2025-08-21
---


## TLDR; 
Low disk space makes HTTP request routing fail due to WASM cache in envoy controller not being loaded properly. This can cause very weird failure pattern where a request only with additional header (routing-strategy) fails with no healthy upstream and a request without this header works perpectly...

## Background and Context

I have been working on my intelligent request routing project for LLM inference applications. It has been built based on [AIBrix](https://github.com/vllm-project/aibrix). I set up a local dev environment on my macbook for faster development and debugging to avoid docker image push to and pull from the remote repository on the remote k8s cluster. The AIBrix installation was done correctly and curl test was also successful. However, it stopped working after I have a lunch... Finding out the root cause of the http request failure was tricky because the error was just saying it fails due to no healthy upstream but all AIBrix components were up running including the vllm app. And none of the components (aibrix controller manager, envoy gateway, aibrix gateway plugin, etc.) were telling what the problem was. 

In this blog, I am going to talk about the troubleshooting process. It turned out a simple issue but it didn't manifest at all and so hard to find since it was hidden like a ring lost in a beach. 

## AIBrix Infrastructure Overview

AIBrix is a scalable cloud-native infrastructure for LLM inference applications. While it provides many capabilities including auto-scaling, model serving, resource management, multi-tenancy, and cost optimization, this debugging session focuses specifically on its intelligent request routing feature.

The routing intelligence is one key feature among many others that AIBrix provides:

- Auto-scaling based on inference workload patterns
- Model serving with vLLM, TensorRT-LLM, and other framework integrations
- Resource management for optimal GPU/CPU allocation
- Multi-tenancy for serving multiple models and users
- Cost optimization through intelligent resource scheduling
- Observability for comprehensive LLM workload monitoring


### Control Plane vs Data Plane Architecture

The system follows the standard separation of concerns used by modern service mesh and API gateway solutions (Istio, Consul Connect, AWS App Mesh, Linkerd, Kong):

**Control Plane (configuration management):**

- Envoy Gateway Controller: Translates Gateway API resources into Envoy configurations
- AIBrix Controller Manager: Manages AIBrix-specific resources and model discovery

**Data Plane (traffic processing):**

- Envoy Proxy Instance: Processes actual HTTP requests and applies routing rules
  - `envoy-aibrix-system-aibrix-eg-903790dc` deployment and its pod
- aibrix-gateway-plugins: Provides LLM-specific routing intelligence
  - `aibrix-gateway-plugins` and its pod
- Model Services: Execute inference workloads
  - vllm pods

### Core Components

**AIBrix Controller Manager (aibrix-controller-manager):** Manages custom resources like ModelAdapters and handles auto-discovery of LLM model deployments. It watches for pods with specific labels and automatically creates routing configurations. This component runs the AIBrix control plane logic.

**Envoy Gateway Controller (envoy-gateway):** The upstream Envoy Gateway project controller that translates Kubernetes Gateway API resources (Gateway, GatewayClass, HTTPRoute) into Envoy proxy configurations. This is the standard Envoy Gateway controller that acts as a "compiler" converting high-level Gateway API resources into low-level Envoy configuration.

**Envoy Proxy Instance (envoy-aibrix-system-aibrix-eg-903790dc):** The actual Envoy proxy pod that handles incoming requests and processes all HTTP traffic. This is the data plane component that applies routing rules, performs load balancing, and communicates with upstream services. It's created and managed by the Envoy Gateway controller based on Gateway resource configurations.

**aibrix-gateway-plugins (aibrix-gateway-plugins):** The core AIBrix routing intelligence engine that implements LLM-specific routing strategies. This component receives requests from the Envoy proxy via the external processing mechanism and makes intelligent routing decisions based on factors like current load, model warm-up state, cache efficiency, SLA requirements, and resource utilization.

**Model Services (llama2-7b, mock-app):** The actual LLM serving applications that process inference requests. These can be vLLM, TensorRT-LLM, or other model serving frameworks integrated with AIBrix.

## Request Lifecycle in AIbrix
Regarding the http request lifecycle, it first touches aibrix-gateway-plugins (envoy external service), the aibrix-gateway-plugins sends it to aibrix-gateway-plugins. After aibrix-gateway-plugin runs routing algorithm, it returns the request back to the aibrix-gateway-plugins with target pod, and then the aibrix-gateway-plugins forwards the request to the appropriate vllm pod.
Let's take a look at each of the components involved in request lifecycle to have better understanding of their role.

AIBrix leverages Envoy Proxy rather than building a custom proxy because it needs:

- High-performance HTTP/gRPC traffic handling for LLM inference workloads
- Advanced load balancing with health checking and circuit breaking
- Production-grade observability with metrics, tracing, and logging
- Extensibility through filters and external processing for AI-specific routing logic
- Cloud-native integration with Kubernetes service discovery

This allows AIBrix to focus on LLM-specific optimizations while leveraging proven proxy infrastructure.

### Request Processing Flow

The request processing involves multiple layers in the data plane, with control plane components managing configuration but not touching actual requests:

1. Client Request → Port-forward (localhost:8888)
2. Port-forward → Envoy Proxy Instance (envoy-aibrix-system-aibrix-eg-903790dc)
3. Envoy Proxy → Route matching based on HTTPRoute configurations (managed by Envoy Gateway Controller)
4. Route Decision Branch:
  - Direct Routes: Requests with `model: llama2-7b` header → Direct to model service (llama2-7b:8080)
  - Extension Processing: Requests with `routing-strategy` header → EnvoyExtensionPolicy triggers external processing
5. Envoy Proxy → aibrix-gateway-plugins service (via external processing filter)
  - aibrix-gateway-plugins is an external processing service that Envoy calls via gRPC through the external processing filter. It runs routing algorithm.
6. aibrix-gateway-plugins → Envoy proxy
  - aibrix-gateway-plugins returns selected pod to envoy proxy
7. Envoy proxy → selected vllm pod
  - Forwards request to selected pod

**Note:** The Envoy Gateway Controller and AIBrix Controller Manager are control plane components that manage configuration but do not process actual requests. They only configure the data plane components that handle traffic.

### **Envoy Gateway Controller** 
It reads Gateway API resources and generates Envoy configuration:

- Converts HTTPRoute resources into Envoy route configurations
- Manages the lifecycle of Envoy proxy pods
- Applies EnvoyExtensionPolicy configurations as Envoy external processing filters

### **Envoy Proxy Instance (envoy-aibrix-system-aibrix-eg-903790dc)** 
It is the critical data plane component:

- Receives all incoming HTTP requests
- Applies routing rules generated by Envoy Gateway Controller
- For extension policy routes, forwards requests to external processing services
- Handles load balancing, health checking, and traffic management

### **aibrix-gateway-plugins** 
It provides the intelligence layer:

- Receives requests from Envoy via gRPC external processing API
- Maintains model metadata and performance metrics
- Implements various routing algorithms based on the routing-strategy header
- Returns routing decisions back to Envoy proxy

This architecture allows AIBrix to leverage standard Envoy Gateway functionality while adding intelligent routing capabilities through the extension mechanism.

## Problem Description

The issue manifested as a http request failure that was highly specific to request headers:
(Again, it was working originally. After I had food, it stopped working...)

This is the curl that needs to success. routing-strategy is specified as a header. model and message are specified in the body.

```bash
curl -v http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "routing-strategy: random" \
  -d '{"model": "llama2-7b", "messages": [{"role": "user", "content": "test"}]}'
```

It failed, saying **HTTP 503, "no healthy upstream"**.



However, after testing different curl requests, I found curl succeeded when it routing-strategy header is omitted.... This is very weird.

**Working request:**
```bash
curl -v http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "model: llama2-7b" \
  -d '{"model": "llama2-7b", "messages": [{"role": "user", "content": "test"}]}'
```
**Result:** HTTP 200!


Let's take a look at what the difference between the above two failing and successful requests are. The Envoy access logs from the proxy instance (envoy-aibrix-system-aibrix-eg-903790dc) shows critical differences between working and failing requests. Let's examine both cases:

```bash
kubectl logs envoy-aibrix-system-aibrix-eg-903790dc-7c8dd7d4b9-64w68 -n envoy-gateway-system
```

**Working request logs (with model: llama2-7b and without routing-strategy header):**
```json
{":authority":"localhost:8888","bytes_received":73,"bytes_sent":302,"connection_termination_details":null,"downstream_local_address":"127.0.0.1:10080","downstream_remote_address":"127.0.0.1:55222","duration":6,"method":"POST","protocol":"HTTP/1.1","requested_server_name":null,"response_code":200,"response_code_details":"via_upstream","response_flags":"-","route_name":"httproute/aibrix-system/llama2-7b-router/rule/0/match/1/*","start_time":"2025-08-20T23:21:58.905Z","upstream_cluster":"httproute/aibrix-system/llama2-7b-router/rule/0","upstream_host":"10.244.0.19:8000","upstream_local_address":"10.244.0.30:48658","upstream_transport_failure_reason":null,"user-agent":"curl/8.7.1","x-envoy-origin-path":"/v1/chat/completions","x-envoy-upstream-service-time":null,"x-forwarded-for":"10.244.0.30","x-request-id":"4000a69d-3db6-404c-8892-4f8023e008f0"}
```

Ignore other parts but see **"route_name":"httproute/aibrix-system/llama2-7b-router/rule/0/match/1/*"**. Envoy proxy finds the right route.

**Failing request logs (with 'routing-strategy' header):**
```json
{":authority":"localhost:8888","bytes_received":0,"bytes_sent":19,"connection_termination_details":null,"downstream_local_address":"127.0.0.1:10080","downstream_remote_address":"127.0.0.1:47350","duration":0,"method":"POST","protocol":"HTTP/1.1","requested_server_name":null,"response_code":503,"response_code_details":"no_healthy_upstream","response_flags":"UH","route_name":"original_route","start_time":"2025-08-21T03:23:19.513Z","upstream_cluster":"original_destination_cluster","upstream_host":null,"upstream_local_address":null,"upstream_transport_failure_reason":null,"user-agent":"curl/8.7.1","x-envoy-origin-path":"/v1/chat/completions","x-envoy-upstream-service-time":null,"x-forwarded-for":"10.244.0.34","x-request-id":"34137566-5a0d-4835-878e-bfebcb2e67fd"}
```

Again, ignoring other parts but see **"route_name":"original_route"**. This is envoy proxy falling back to the original route. In Envoy Proxy, original_route is a default route name used as a fallback when the HTTP request doesn't match any of the explicitly defined routes in the configuration. The orignal_route here is localhost(127.0.0.1) and port 8888 in ip table. 

Envoy receives the request and, based on its routing rules, forwards it to a different, internal service (vllm pods in our context). The source IP of the new connection from Envoy to the internal service is Envoy's own IP address, not the original client's IP. 

So original_route will fail. We need the route given by envoy which is `httproute/aibrix-system/llama2-7b-router/rule/0/match/1/*`.


### What this tells us:

The **working request** shows that Envoy successfully:

- Matched a configured HTTPRoute: `httproute/aibrix-system/llama2-7b-router/rule/0/match/1/*`
- Found a healthy upstream cluster: `httproute/aibrix-system/llama2-7b-router/rule/0`
- Connected to the actual pod: `10.244.0.19:8000`
- Received a response from the backend: `via_upstream`

The **failing request** shows that Envoy:

- Fell back to default routing: `original_route` (not a configured HTTPRoute)
- Used fallback cluster: `original_destination_cluster` (not a real backend)
- Found no upstream: `upstream_host: null`
- Had no backend to connect to: `no_healthy_upstream`

This pattern suggested that requests with routing-strategy headers were not matching any of the configured HTTPRoutes and were falling back to a default route with no available upstream. The `original_route` is Envoy's fallback mechanism when no configured routes match the request, indicating a routing configuration or processing issue rather than a backend availability problem.

## Investigations...
Investigating the symptom, requests with routing-strategy headers falls back to original_route and failed

### Route Precedence Investigation

**Reasoning:** Since the routing behavior differed based on headers, we suspected that multiple HTTPRoutes were conflicting, causing requests to match the wrong route before reaching the extension processing pipeline.

Gateway API processes routes in a specific order, and I thought the issue might be related to route precedence - where a broader route was capturing requests before a more specific route could match them.

Let's check the HTTPRoute configurations. There are three HTTPRoute resources.
```bash
kubectl get httproutes -A --sort-by=.metadata.creationTimestamp

NAMESPACE       NAME                                     HOSTNAMES   AGE
aibrix-system   aibrix-reserved-router-models-endpoint               12h
aibrix-system   aibrix-reserved-router                               8h  
aibrix-system   llama2-7b-router                                     6h
```

```bash
kubectl describe httproute -A
```
```yaml
# aibrix-reserved-router - handles requests for extension processing
spec:
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/chat/completions
    backendRefs:
    - name: aibrix-gateway-plugins
      port: 50052

# llama2-7b-router - handles direct model requests
spec:
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/chat/completions
      headers:
      - name: model
        type: Exact
        value: llama2-7b
    backendRefs:
    - name: llama2-7b
      port: 8000
```

Let's see llama2-7b-router status.
```bash
kubectl describe httproute llama2-7b-router -n aibrix-system

Status:
  Conditions:
    Type:    Accepted
    Status:  True
    Message: Route is accepted
    Type:    ResolvedRefs  
    Status:  True
    Message: Resolved all the Object references for the Route
```

All routes showed "Accepted" status, indicating the route configurations were valid. 

We also verified the Envoy proxy was receiving these configurations:
```bash
kubectl logs envoy-aibrix-system-aibrix-eg-903790dc-7c8dd7d4b9-64w68 -n envoy-gateway-system | grep -i "route\|config"
```

The proxy logs showed it was receiving route updates, but requests with routing-strategy headers were still not matching the expected routes.

So..... the route configurations were not the problem - the Envoy proxy instance was receiving valid configurations, **but something in the extension processing pipeline was causing requests to bypass the normal routing logic.**

### Header Matching Syntax Analysis
The Envoy proxy logs contained deprecation warnings about header matching syntax, suggesting that the header matching mechanism in the proxy might not be working correctly. Though, it should not be the reason since it worked earlier!!! But I was not trusting anything so let's check...

**Envoy proxy deprecation warnings:**
```bash
kubectl logs envoy-aibrix-system-aibrix-eg-903790dc-7c8dd7d4b9-64w68 -n envoy-gateway-system

[WARNING] Deprecated field: type envoy.config.route.v3.HeaderMatcher Using deprecated option 'envoy.config.route.v3.HeaderMatcher.exact_match'
```

I hypothesized that this deprecated syntax might be causing header matching to fail within the Envoy proxy, particularly for complex header combinations.

```bash
kubectl edit httproute llama2-7b-router -n aibrix-system
```

```yaml
# Changed from:
headers:
- name: model
  type: Exact
  value: llama2-7b

# Changed to:
headers:
- name: model
  value: llama2-7b
```

I tried removing the `type: Exact` field.

After applying the changes, we verified the Envoy proxy received the updated configuration:
However, the routing behavior remained unchanged. Requests with just the model header continued to work, while requests with routing-strategy headers still failed. So, this is not the root cause. I was not haunted as bad as I thought...

### Configuration Comparison between problematic local kind cluster and working remote cluster

**Reasoning:** Since we had access to a working cluster with identical AIBrix setup, we decided to compare configurations to identify any differences that might explain the behavior variance between the working and non-working environments.


```bash
kubectl get envoyproxy aibrix-custom-proxy-config -n aibrix-system -o yaml
kubectl get gateway aibrix-eg -n aibrix-system -o yaml  
kubectl get gatewayclass aibrix-eg -o yaml
kubectl get httproutes -A -o yaml
```

EnvoyProxy configurations were identical

The Envoy proxy pod configurations, including image versions, resource allocations, and environment variables, were identical between clusters.

And all other configurations were also same... It was driving me crazy.

### Extension Policy Investigation (Actual Root Cause)

**Reasoning:** Since the previous investigations had ruled out basic configuration issues, I decided to examine the extension processing pipeline more closely. The fact that requests with routing-strategy headers were hitting "original_route" in the Envoy proxy suggested that the EnvoyExtensionPolicy mechanism was failing.

We checked the Envoy Gateway controller logs specifically for routing-related errors:

```bash
kubectl logs -n envoy-gateway-system deployment/envoy-gateway | grep -i "routing"

2025-08-21T03:22:49.283Z ERROR xds-translator failed to translate xds ir 
"match":{"headers":[{"name":"routing-strategy","string_match":{"safe_regex":{"regex":".*"}}}],"prefix":"/v1"},
"name":"original_route",
"route":{"cluster":"original_destination_cluster","timeout":"120s"},
"typed_per_filter_config":{"envoy.filters.http.ext_proc/envoyextensionpolicy/aibrix-system/aibrix-gateway-plugins-extension-policy/extproc/0"
err:invalid RouteConfiguration.VirtualHosts[0]: embedded message failed validation
```

Oh OH OH Oh...
**There was indeed a special route being created for routing-strategy headers**
It was associated with an EnvoyExtensionPolicy (aibrix-gateway-plugins-extension-policy)
The extension policy configuration was failing validation
This caused requests to fall back to the "original_route" with no healthy upstream

(envoyextensionpolicy was a resource we were missing... who thinks it is the root cause...)
**Extension policy status check:**
```bash
kubectl describe envoyextensionpolicy aibrix-gateway-plugins-extension-policy -n aibrix-system

Status:
  Conditions:
    Type:    Accepted
    Status:  False
    Reason:  Invalid  
    Message: Wasm: wasm cache is not initialized.
```

Oh Oh Oh, my boi.

The extension policy was failing specifically because the WASM cache could not be initialized. This failure was preventing the Envoy proxy from properly configuring the external processing filter that handles requests destined for the aibrix-gateway-plugins.

When a request lacks the routing-strategy header but includes 'model: llama2-7b', it matches the llama2-7b-router HTTPRoute directly. Envoy routes it straight to the vLLM pod using the configured backend reference, bypassing any extension processing entirely. This path works because it doesn't depend on the broken WASM cache.

When a request includes the routing-strategy header, it should match the aibrix-reserved-router HTTPRoute, which is configured to trigger the EnvoyExtensionPolicy for external processing through aibrix-gateway-plugins. However, due to the WASM cache initialization failure, the extension policy cannot be properly instantiated in Envoy's filter chain. This causes the request to fail route matching entirely, falling back to Envoy's default "original_route" - a passthrough route with no configured upstream, resulting in the "no healthy upstream" error.

In summary,

**With model: llama2-7b header (no routing-strategy):**

Matches the llama2-7b-router HTTPRoute directly
Route: httproute/aibrix-system/llama2-7b-router/rule/0/match/1/*
Goes directly to the vLLM pod at 10.244.0.19:8000
No extension processing involved


**With routing-strategy header:**

Should match the aibrix-reserved-router HTTPRoute
Should trigger EnvoyExtensionPolicy for external processing
But fails due to WASM cache issue
Falls back to original_route (which has no valid upstream)


### WASM Cache Analysis

**Reasoning:** With the WASM cache initialization failure identified, we needed to understand why the cache couldn't be created. WASM (WebAssembly) is used by Envoy for extending functionality through external processing filters. If the cache can't be initialized, extension policies will fail, and the Envoy proxy will fall back to default routing behavior.

**Key diagnostic command:**
```bash
kubectl logs -n envoy-gateway-system deployment/envoy-gateway | grep -i "wasm\|cache\|init"
```

**Critical output:**
```
2025-08-21T03:49:15.867Z ERROR gateway-api Failed to create Wasm cache directory
{"runner": "gateway-api", "error": "mkdir /var/lib/eg/wasm: no space left on device"}
```

This log entry immediately revealed the root cause - the system was running out of disk space and couldn't create the WASM cache directory that the Envoy Gateway controller needed for extension policy processing.

**Verification:**
```bash
docker exec kind-control-plane df -h
```

**Output:**
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        59G   59G     0 100% /
```

The kind cluster's filesystem was completely full. We also checked the specific impact on the Envoy proxy:

```bash
kubectl logs envoy-aibrix-system-aibrix-eg-903790dc-7c8dd7d4b9-64w68 -n envoy-gateway-system | grep -i "wasm\|cache"
```

The proxy logs confirmed it was not receiving proper extension filter configurations due to the upstream WASM cache failure.

## Root Cause

The issue was caused by **disk space exhaustion in the kind cluster**, which had a cascading effect through the entire request processing pipeline:

### Failure Chain

1. **Disk space exhaustion:** The kind cluster filesystem reached 100% capacity
2. **WASM cache initialization failure:** Envoy Gateway controller could not create `/var/lib/eg/wasm` directory. Note that envoy gateway controller is different from data plane envoy proxy.
3. **Extension policy failure:** EnvoyExtensionPolicy (aibrix-gateway-plugins-extension-policy) failed with "Wasm: wasm cache is not initialized"
4. **Envoy configuration corruption:** The Envoy proxy instance (envoy-aibrix-system-aibrix-eg-903790dc) received invalid route configurations from envoy gateway controller for requests needing extension processing with routing-strategy header.
5. **Routing fallback:** Requests with routing-strategy headers fell back to "original_route" which had no healthy upstream
6. **Selective impact:** Only requests requiring extension processing were affected; direct routes continued working

**Extension Policy Configuration**

The failing extension policy was configured as follows:

```yaml
apiVersion: gateway.envoyproxy.io/v1alpha1
kind: EnvoyExtensionPolicy
metadata:
  name: aibrix-gateway-plugins-extension-policy
  namespace: aibrix-system
spec:
  targetRef:
    kind: HTTPRoute
    name: aibrix-reserved-router
  extProc:
  - backendRefs:
    - name: aibrix-gateway-plugins
      port: 50052
    messageTimeout: 60s
    processingMode:
      request:
        body: Buffered
      response:
        body: Streamed
```

This policy was designed to:

- Intercept requests matching the aibrix-reserved-router HTTPRoute
- Forward them to the aibrix-gateway-plugins for external processing
- Apply intelligent routing decisions based on the routing-strategy header

### Request Flow Breakdown

**Working flow (direct model requests):**

1. Request with `model: llama2-7b` header → Envoy proxy
2. Envoy matches llama2-7b-router HTTPRoute
3. Direct routing to model service (no extension processing required)
4. Model service processes request and returns response

**Broken flow (routing-strategy requests):**

1. Request with `routing-strategy` header → Envoy proxy
2. Envoy attempts to match extension processing route
3. Extension policy configuration is invalid due to WASM cache failure
4. Request falls back to original_route with original_destination_cluster
5. No healthy upstream available → 503 error

## Solution

The solution involved addressing the root cause and restarting the affected components:

**Disk cleanup:**
```bash
docker system prune -f
docker image prune -a -f
docker volume prune -f
```

**Verify space recovery:**
```bash
docker exec kind-control-plane df -h
```

**Restart Envoy Gateway controller (to reinitialize WASM cache):**
```bash
kubectl rollout restart deployment/envoy-gateway -n envoy-gateway-system
kubectl rollout status deployment/envoy-gateway -n envoy-gateway-system
```

**Restart Envoy proxy instance (to apply corrected configuration):**
```bash
kubectl rollout restart deployment/envoy-aibrix-system-aibrix-eg-903790dc -n envoy-gateway-system
kubectl rollout status deployment/envoy-aibrix-system-aibrix-eg-903790dc -n envoy-gateway-system
```

**Verification of fix:**
```bash
kubectl describe envoyextensionpolicy aibrix-gateway-plugins-extension-policy -n aibrix-system
```

**Output after fix:**
```
Status:
  Conditions:
    Type:    Accepted
    Status:  True
    Message: Policy has been accepted.
```

**Verify Envoy proxy configuration:**
```bash
kubectl logs envoy-aibrix-system-aibrix-eg-903790dc-7c8dd7d4b9-64w68 -n envoy-gateway-system | grep -i "config\|route"
```

The logs confirmed the proxy was now receiving valid route configurations with proper extension processing filters.

**Functional test:**
```bash
curl -v http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "routing-strategy: random" \
  -d '{"model": "llama2-7b", "messages": [{"role": "user", "content": "test"}]}'
```

**Result:** HTTP 200, proper routing through the complete AIBrix pipeline:

1. Request → Envoy proxy
2. Envoy proxy → Extension processing → aibrix-gateway-plugins
3. aibrix-gateway-plugins → Intelligent routing decision → Model service
4. Model service → Response

## Key Takeaways

This debugging session highlighted several important lessons about complex distributed systems:

1. **Infrastructure dependencies cascade:** A simple infrastructure issue (disk space) can cause failures in sophisticated features (extension processing) that appear unrelated. The failure path went from disk space → WASM cache → extension policy → Envoy configuration → routing behavior.

2. **Component interaction complexity:** Modern service mesh architectures involve multiple layers (Envoy Gateway controller, Envoy proxy instances, extension policies, external processing services) where each layer can fail independently and cause different symptoms.

3. **Logging strategy matters:** The critical error was buried in the Envoy Gateway controller logs, not in the more obvious places like the Envoy proxy access logs or the AIBrix application logs. Understanding which component logs contain the most actionable information is crucial for efficient debugging.

4. **Extension mechanism fragility:** Extension-based architectures (like EnvoyExtensionPolicy) add powerful capabilities but also introduce additional failure modes. When extensions fail, systems often fall back to unexpected default behaviors that can be difficult to diagnose.

5. **Infrastructure-first debugging:** Even in complex distributed systems with sophisticated routing logic, basic infrastructure issues (disk space, memory, network) should be checked early in the debugging process.

## Some complain

It was another frustrating collapse in k8s cluster. The root cause was something unexpected and the clue was buried deep in the infra structure. The same painful patterns arose a lot of times in other issues I encountered. It was so hard to find and fix because each component in the infra is distributed and when an issue occurs, it does not forward it to other stack or other infra component. When a problem X happens in component A and if there is component B is interacting with A related to the problem X, the component B often says something vague which can confuses the operator and it does not say the root cause which happened at A. I think this is hard to achieve vertically connecting them so any issue is not easily traceable across the system. Maybe it is architectural challenge.. 