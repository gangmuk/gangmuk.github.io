---
layout: post
title: "AIBrix Architecture Documentation"
date: 2025-08-24
---

# AIBrix Architecture Documentation

## System Architecture Overview

### Control Plane
```
┌─────────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │ Envoy Gateway       │    │ AIBrix Controller Manager        │ │
│  │ Controller          │    │                                  │ │
│  │                     │    │ - Watches for model pods         │ │
│  │ - Reads HTTPRoutes  │    │ - Creates HTTPRoutes             │ │
│  │ - Reads EEPs        │    │ - Creates EnvoyExtensionPolicies │ │
│  │ - Generates xDS     │    │ - Manages ModelAdapters          │ │
│  │ - Manages WASM cache│    │                                  │ │
│  └─────────────────────┘    └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Data Plane
```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA PLANE                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │ Envoy Proxy         │    │ AIBrix Gateway Plugins           │ │
│  │ Instance            │    │ (External Service)               │ │
│  │                     │    │                                  │ │
│  │ - Receives xDS      │◄──►│ - Receives gRPC calls from Envoy │ │
│  │ - Applies filters   │    │ - Runs routing algorithms        │ │
│  │ - Routes requests   │    │ - Returns routing decisions      │ │
│  │ - Calls ext-proc    │    │                                  │ │
│  └─────────────────────┘    └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        ┌──────────────────────┐
                        │    Model Services    │
                        │   (vLLM pods, etc)   │
                        └──────────────────────┘
```

## How Components Process Extensions 🔄

### Step 1: Resource Creation (Who Creates What)

AIBrix Controller Manager automatically creates:

**HTTPRoute for extension processing:**
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: aibrix-reserved-router
spec:
  rules:
  - matches:
    - path:
        type: PathPrefix  
        value: /v1/chat/completions
    backendRefs:
    - name: aibrix-gateway-plugins  # Points to external service
      port: 50052
```

**EnvoyExtensionPolicy for external processing:**
```yaml
apiVersion: gateway.envoyproxy.io/v1alpha1
kind: EnvoyExtensionPolicy
metadata:
  name: aibrix-gateway-plugins-extension-policy
spec:
  targetRef:
    kind: HTTPRoute
    name: aibrix-reserved-router
  extProc:
  - backendRefs:
    - name: aibrix-gateway-plugins
      port: 50052
```

### Step 2: Extension Processing Pipeline

**What "Extension Management" Processes:**

- **Policy Validation**: Envoy Gateway validates the EnvoyExtensionPolicy
- **Metadata Storage**: Stores extension configuration in WASM cache
- **xDS Generation**: Creates Envoy filter configurations
- **Filter Deployment**: Sends configurations to Envoy proxy instances

### Step 3: xDS (eXtensible Data Source) Explained 📡

xDS is Envoy's configuration protocol. It's how the control plane tells data plane components what to do.

```
Envoy Gateway Controller
        │
        │ (generates xDS messages)
        ▼
┌─────────────────────┐
│   xDS Messages      │
│                     │
│ - Listener config   │
│ - Route config      │  
│ - Cluster config    │
│ - Filter config     │
└─────────────────────┘
        │
        │ (gRPC/HTTP)
        ▼
    Envoy Proxy
```

In your case, xDS contains:

- **Listener Configuration**: "Listen on port 10080"
- **Route Configuration**: "Match /v1/chat/completions with routing-strategy header"
- **Cluster Configuration**: "aibrix-gateway-plugins is at IP:PORT"
- **Filter Configuration**: "Use external processing filter, call aibrix-gateway-plugins via gRPC"

## Complete Request Flow with All Components 🚀

### Configuration Phase (Control Plane)

1. **AIBrix Controller Manager**:
   - Watches for pods with `app: llama2-7b` labels
   - Creates `aibrix-reserved-router` HTTPRoute
   - Creates `aibrix-gateway-plugins-extension-policy` EnvoyExtensionPolicy

2. **Envoy Gateway Controller**:
   - Reads HTTPRoute resources
   - Reads EnvoyExtensionPolicy resources
   - Processes extension through extension system (requires WASM cache)
   - Generates xDS configurations
   - Sends xDS to Envoy proxy instances

### Runtime Phase (Data Plane)

1. **Client Request** → Envoy Proxy Instance
2. **Envoy Proxy** applies route matching:
   - Has `routing-strategy` header? → Triggers external processing filter
   - Has only `model: llama2-7b`? → Direct route to vLLM pod
3. **External Processing Filter** (configured via xDS) → gRPC call to AIBrix Gateway Plugins
4. **AIBrix Gateway Plugins** → Returns routing decision
5. **Envoy Proxy** → Forwards to selected vLLM pod

## What Failed in Your Case ❌

```
┌─────────────────────────────────────────────┐
│              Failure Chain                  │
├─────────────────────────────────────────────┤
│  1. Disk full                               │
│     ↓                                       │
│  2. Can't create /var/lib/eg/wasm           │
│     ↓                                       │
│  3. Extension processing system fails       │
│     ↓                                       │
│  4. EnvoyExtensionPolicy marked Invalid     │
│     ↓                                       │
│  5. No proper xDS for external processing   │
│     ↓                                       │
│  6. Requests fall back to original_route    │
│     ↓                                       │
│  7. HTTP 503 "no healthy upstream"          │
└─────────────────────────────────────────────┘
```

## Key Components Summary

- **AIBrix Controller Manager**: Watches pods and creates routing resources
- **Envoy Gateway Controller**: Manages xDS configuration and WASM cache
- **Envoy Proxy**: Routes requests and applies filters
- **AIBrix Gateway Plugins**: External service for routing decisions
- **xDS**: Configuration protocol between control and data planes
- **WASM Cache**: Required for extension processing (failed due to disk space)