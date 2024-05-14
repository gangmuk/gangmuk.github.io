---
layout: post
title:  "K8S cheat sheet"
date:   2024-05-14 14:22:40
blurb: "A look at an example post using Bay Jekyll theme."
og_image: /assets/img/content/post-example/Banner.jpg
---

<img src="{{ "/assets/img/content/post-example/Banner.jpg" | absolute_url }}" alt="bay" class="post-pic"/>
<br />
<br />

This K8S cheat sheet is not organized at all. It started as a small note to cache what I often repetiviely search. It was created at Aug 2023
<br />


#### Table of Contents
- [k8s-cheatsheet-GM](#k8s-cheatsheet-gm)
    - [Install kind cluster.](#install-kind-cluster)
    - [Create a cluster with yaml config file.](#create-a-cluster-with-yaml-config-file)
    - [Check currently existing clusters.](#check-currently-existing-clusters)
    - [Check currently existing clusters and it shows the cluster that is coupled to the kubectl.](#check-currently-existing-clusters-and-it-shows-the-cluster-that-is-coupled-to-the-kubectl)
    - [Change the kubectl context from other cluster to `kind-text-cluster`.](#change-the-kubectl-context-from-other-cluster-to-kind-text-cluster)
    - [Connect to the node (remember node in KinD cluster is docker container.)](#connect-to-the-node-remember-node-in-kind-cluster-is-docker-container)
    - [Apply config to the cluster.](#apply-config-to-the-cluster)
    - [Update and roll out container image.](#update-and-roll-out-container-image)
    - [kubectl command dictionary](#kubectl-command-dictionary)
    - [How to get kube-scheduler config yaml file.](#how-to-get-kube-scheduler-config-yaml-file)
    - [Other kind commands](#other-kind-commands)
  - [Logging](#logging)
      - [Where is the log file.](#where-is-the-log-file)
      - [How to get pods or deployment log](#how-to-get-pods-or-deployment-log)
      - [How to change the log level of kubelet](#how-to-change-the-log-level-of-kubelet)
    - [`kubectl diff -f ...`](#kubectl-diff--f-)
  - [Metric server](#metric-server)
    - [Installation](#installation)
    - [Chagne metrics-server metric-resolution configuration](#chagne-metrics-server-metric-resolution-configuration)
  - [kubectl cp \& docker cp](#kubectl-cp--docker-cp)
      - [Copying file from host to one of kind-node.](#copying-file-from-host-to-one-of-kind-node)
      - [Copying file from one of kind-node to pod.](#copying-file-from-one-of-kind-node-to-pod)
      - [Copying file from host to pod.](#copying-file-from-host-to-pod)
    - [`kubectl autoscale` subcommand](#kubectl-autoscale-subcommand)
    - [Create kind cluster](#create-kind-cluster)
    - [Dump log files](#dump-log-files)
  - [HPA](#hpa)
    - [kubectl get pods to csv format](#kubectl-get-pods-to-csv-format)
    - [Installing kube-scheduler in kind cluster](#installing-kube-scheduler-in-kind-cluster)
    - [Important Notes](#important-notes)
    - [Debugging Kubernetes nodes with crictl (kind cluster uses crictl for container management. It does not use docker.)](#debugging-kubernetes-nodes-with-crictl-kind-cluster-uses-crictl-for-container-management-it-does-not-use-docker)
    - [ADDED INFO HOW TO SETUP MOUNT POINTS](#added-info-how-to-setup-mount-points)
    - [load-generator](#load-generator)
    - [Installing Descheduler](#installing-descheduler)
  - [Taint \& Toleration](#taint--toleration)
    - [How to add and remove taint.](#how-to-add-and-remove-taint)
      - [How to list taints in all nodes.](#how-to-list-taints-in-all-nodes)
  - [Custom column print in kubectl](#custom-column-print-in-kubectl)
    - [Node label](#node-label)
    - [S2](#s2)
    - [Logging](#logging-1)
      - [kubectl get events](#kubectl-get-events)
      - [kubelet log](#kubelet-log)
      - [How to change kube-scheduler log level (verbosity)](#how-to-change-kube-scheduler-log-level-verbosity)
        - [Expected scheduler log output](#expected-scheduler-log-output)
  - [Apply linux tc to a pod.](#apply-linux-tc-to-a-pod)
      - [How to get the name and the ip of a specific pod.](#how-to-get-the-name-and-the-ip-of-a-specific-pod)
      - [linux tc command](#linux-tc-command)
    - [How to delete the network interface of a docker container](#how-to-delete-the-network-interface-of-a-docker-container)
      - [drain, cordon, uncordon](#drain-cordon-uncordon)
    - [Creating pod latency](#creating-pod-latency)
        - [When the image was pulled.](#when-the-image-was-pulled)
        - [When the image is present locally.](#when-the-image-is-present-locally)
    - [Make the node unreachable by stopping kubelet](#make-the-node-unreachable-by-stopping-kubelet)
    - [I deleted the kindnet-xxx pod and it is never created again.](#i-deleted-the-kindnet-xxx-pod-and-it-is-never-created-again)
        - [Solution](#solution)
  - [How to use local docker image in deployment](#how-to-use-local-docker-image-in-deployment)
    - [No disk space in vm having k8s cluster](#no-disk-space-in-vm-having-k8s-cluster)

# k8s-cheatsheet-GM
---

### Install kind cluster.
[2023-04-24]
```shell
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.18.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```
Up-to-date command: https://kind.sigs.k8s.io/docs/user/quick-start/

### Create a cluster with yaml config file.
```shell
kind create cluster --config three_worker_cluster.yaml --name three_worker_cluster
```
Example cluster config having one control node and three worker nodes.
```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
    image: kindest/node:v1.24.7@sha256:577c630ce8e509131eab1aea12c022190978dd2f745aac5eb1fe65c0807eb315
```

---
### Check currently existing clusters.
`kind get clusters`
```shell
test-cluster
three-worker-cluster
```

---
### Check currently existing clusters and it shows the cluster that is coupled to the kubectl.
`kubectl config get-contexts`
```shell
CURRENT   NAME                        CLUSTER                     AUTHINFO                    NAMESPACE
          kind-test-cluster           kind-test-cluster           kind-test-cluster
*         kind-three-worker-cluster   kind-three-worker-cluster   kind-three-worker-cluster
```

---
### Change the kubectl context from other cluster to `kind-text-cluster`.
```shell
kubectl config use-context kind-test-cluster
```

After changing the context, it shows 
```shell
CURRENT   NAME                        CLUSTER                     AUTHINFO                    NAMESPACE
*         kind-test-cluster           kind-test-cluster           kind-test-cluster
          kind-three-worker-cluster   kind-three-worker-cluster   kind-three-worker-cluster
```

---
### Connect to the node (remember node in KinD cluster is docker container.)
Check current containers.
```shell
docker ps
CONTAINER ID   IMAGE                  COMMAND                  CREATED             STATUS             PORTS                       NAMES
f6b6fe4a3059   kindest/node:v1.25.3   "/usr/local/bin/entr…"   About an hour ago   Up About an hour                               three-worker-cluster-worker3
63181f4a7d09   kindest/node:v1.25.3   "/usr/local/bin/entr…"   About an hour ago   Up About an hour   127.0.0.1:46783->6443/tcp   three-worker-cluster-control-plane
c6e2c27cf6d7   kindest/node:v1.25.3   "/usr/local/bin/entr…"   About an hour ago   Up About an hour                               three-worker-cluster-worker
1fe815363a24   kindest/node:v1.25.3   "/usr/local/bin/entr…"   About an hour ago   Up About an hour                               three-worker-cluster-worker2
7ff64f32905d   kindest/node:v1.25.3   "/usr/local/bin/entr…"   3 hours ago         Up 3 hours         127.0.0.1:36841->6443/tcp   test-cluster-control-plane
```
Enter the container which is the node.
```shell
docker exec -it 7ff64f32905d /bin/bash
```

---
### Apply config to the cluster.
This is an exmple. You can replace it with any config file (yaml, json format).
```shell
kubectl apply -f FILENAME
```

```shell
kubectl apply -f https://k8s.io/examples/controllers/nginx-deployment.yaml
kubectl get deployments
```

---
### Update and roll out container image.
```shell
kubectl set image deployment.v1.apps/nginx-deployment nginx=nginx:1.16.1
kubectl edit deployment/nginx-deployment
kubectl rollout status deployment/nginx-deployment
kubectl get p ods
kubectl get deployments
```

---
### kubectl command dictionary
`kubectl get clusters`
`kubectl get nodes`
`kubectl get services`
`kubectl get deployments`
`kubectl get pods`
`kubectl get pods -o wide`
`kubectl get pods -n kube-system`: get all kube-system
`kubectl get pods -n kube-system -l component=kube-scheduler`: get kube-scheduler only among kube-system



---
### How to get kube-scheduler config yaml file.
If you just do get pods without specifying any namespace, then it will automatically refer to the default namespace which is "default".
`kubectl get pods`
```txt
No resources found in default namespace.
```
(It returns no pods because I didn't create any pod from my side. This is not bug.)

Let's list up all existing namespaces.
`kubectl get namespace`
```shell
NAME                 STATUS   AGE
default              Active   47h
kube-node-lease      Active   47h
kube-public          Active   47h
kube-system          Active   47h
local-path-storage   Active   47h
```

If you want to get pods in a specific kube-system, you have to specify, e.g., kube-system.
`kubectl get pods -n kube-system`
```shell
NAME                                                         READY   STATUS    RESTARTS   AGE
coredns-565d847f94-jjqv8                                     1/1     Running   0          47h
coredns-565d847f94-s2zqw                                     1/1     Running   0          47h
etcd-three-worker-cluster-control-plane                      1/1     Running   0          47h
kindnet-66vj6                                                1/1     Running   0          47h
kindnet-77bh2                                                1/1     Running   0          47h
kindnet-7fp29                                                1/1     Running   0          47h
kindnet-cpl8j                                                1/1     Running   0          47h
kube-apiserver-three-worker-cluster-control-plane            1/1     Running   0          47h
kube-controller-manager-three-worker-cluster-control-plane   1/1     Running   0          47h
kube-proxy-4zpsm                                             1/1     Running   0          47h
kube-proxy-9lgbs                                             1/1     Running   0          47h
kube-proxy-gk7vz                                             1/1     Running   0          47h
kube-proxy-kj2jp                                             1/1     Running   0          47h
kube-scheduler-three-worker-cluster-control-plane            1/1     Running   0          47h
```

From this output, we can see **kube-scheduler** is also a **pod**.

Finally, we can find yaml file of kube-scheduler pod.
`kubectl get pods -n kube-system kube-scheduler-three-worker-cluster-control-plane -o yaml`
```yaml
apiVersion: v1
kind: Pod
metadata:
    ...
spec:
  containers:
  - command:
    ...
    image: registry.k8s.io/kube-scheduler:v1.25.3
    imagePullPolicy: IfNotPresent
    ...
```

**Reference**
https://stackoverflow.com/questions/43941772/get-yaml-for-deployed-kubernetes-services


---
### Other kind commands
`kind create cluster --config [config file] --name [cluster-name]`
`kind delete cluster --name [cluster_name]`

---
## Logging
Reference:
- available log: https://kubernetes.io/docs/tasks/debug/debug-cluster/#looking-at-logs


#### Where is the log file.

```shell
> cd /var/log/pods/
> ls
> kube-system_coredns-565d847f94-jjqv8_af8b8e45-4b83-4006-b644-71d359c086d8                       kube-system_kube-controller-manager-three-worker-cluster-control-plane_fcd6d3bbeec3d1ab086460556b97103c
kube-system_coredns-565d847f94-s2zqw_89f7d605-2bb1-4553-bbd7-013b53f1b631                       kube-system_kube-proxy-9lgbs_e48be225-f5cf-4b9c-b324-a926f3a27438
kube-system_etcd-three-worker-cluster-control-plane_d7a10b0311e9ed1787410c36191e084f            kube-system_kube-scheduler-three-worker-cluster-control-plane_ac6d9353d5cd622db7510b4a0edc4754
kube-system_kindnet-66vj6_5d30ac56-d5f9-4c90-b341-0bf060dbfb29                                  local-path-storage_local-path-provisioner-684f458cdd-zh4p7_7c1b1df5-a091-499f-a524-b98a44848015
kube-system_kube-apiserver-three-worker-cluster-control-plane_8f76ac2038ffd0f7b97025ee126735ae
```

#### How to get pods or deployment log
`kubectl logs -n [namespace] [type]/[target_name]`
Example
- pod
  - kube-scheduler
    `kubectl logs -n kube-system pods/kube-scheduler-three-worker-cluster-control-plane`
  - metrics-server
    `kubectl logs -n kube-system pods/metrics-server-9bf64b57-bh6sk`
- deployment
  - metrics-server
    `kubectl logs -n kube-system deploy/metrics-server`

---
#### How to change the log level of kubelet
1. ssh to the master node
2. append `/var/lib/kubelet/kubeadm-flags.env file` with `--v=[1-10]`. (higher log level more log printed)
    `KUBELET_KUBEADM_ARGS=--cgroup-driver=cgroupfs --network-plugin=cni --pod-infra-container-image=k8s.gcr.io/pause:3.1 --v=10`
    v=10 will log all the detailed scheduling decisions which is what we want.
3. restart kubelet service.
    `sudo systemctl restart kubelet`
https://stackoverflow.com/questions/55739315/how-to-enable-kubelet-logging-verbosity

---
### `kubectl diff -f ...`
Before applying any changes, always check with 
`kubectl diff -f ...`
but changing with the 
`kubectl apply set-last-applied`
`kubectl apply edit-last-applied`

---
## Metric server
### Installation
```shell
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Even after installing metrics-server, `kubectl top node/pod' command does not work.
```shell
kubectl top node
Error from server (ServiceUnavailable): the server is currently unable to handle the request (get nodes.metrics.k8s.io)
```

If you check pods and deployment in kube-system namespace. You can see that metrics-server does not have any ready pod.
```shell
kubectl get pods -n kube-system

NAME                                                         READY   STATUS    RESTARTS   AGE
...
coredns-565d847f94-jjqv8                                     1/1     Running   0          2d2h
kube-apiserver-three-worker-cluster-control-plane            1/1     Running   0          2d2h
kube-controller-manager-three-worker-cluster-control-plane   1/1     Running   0          2d2h
kube-scheduler-three-worker-cluster-control-plane            1/1     Running   0          2d2h
metrics-server-8ff8f88c6-87x54                               0/1     Running   0          41m
...
```

```shell
kubectl get deployments -n kube-system

NAME             READY   UP-TO-DATE   AVAILABLE   AGE
coredns          2/2     2            2           2d2h
metrics-server   0/1     1            0           40m
```

Let's try to edit config yaml file. That will open a text editor with the deployment yaml file of metrics-server.
```shell
kubectl edit deploy -n kube-system metrics-server
```


It is said that `kube-apiserver` must enable an aggregation layer.
TODO: However, I have no idea how to enable it...
https://github.com/kubernetes-sigs/metrics-server#requirements

kube-apiserver command is not found.
```shell
kube-apiserver
zsh: command not found: kube-apiserver
```


I checked the metrics servier log.
```shell
kubectl logs -n kube-system deploy/metrics-server

...
"Failed to scrape node" err="Get \"https://172.18.0.5:10250/metrics/resource\": x509: cannot validate certificate for 172.18.0.5 because it doesn't contain any IP SANs" node="three-worker-cluster-worker"
...
```

`kubectl get pods -n kube-system` `kubectl get deployments -n kube-system` commands show no running metrics-server.
```shell
kubectl get pods -n kube-system
NAME                                                         READY   STATUS    RESTARTS   AGE
...
metrics-server-8ff8f88c6-87x54                               0/1     Running   0          4m13s
```
```shell
kubectl get deployments -n kube-system
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
coredns          2/2     2            2           2d2h
metrics-server   0/1     1            1           54m
```


The solution was found. I don't understand what the problem was and how it solves the problem. anyway,
solution: https://stackoverflow.com/questions/57137683/how-to-troubleshoot-metrics-server-on-kubeadm
Open the metrics-server yaml file.
```shell
kubectl edit deploy -n kube-system metrics-server
```
Add  **- --kubelet-insecure-tls** under `spec.template.spec.containers`.
```yaml
spec:
    template:
        spec:
            containers:
            - args:
            - --cert-dir=/tmp
            - --kubelet-insecure-tls ## This is added line.
            - --secure-port=4443
            - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
            - --kubelet-use-node-status-port
            - --metric-resolution=15s
...
```

Save and exit the file with `:wq`. After roughly 15-30s, you can use `kubectl top node/pod` command.


Updated yaml file of metrics-server will roll out a new pod for metrics-server. For the first couple seconds, you might see two metrics-server.
```shell
kubectl get pods -n kube-system
metrics-server-8ff8f88c6-87x54                               0/1     Running   0          47m
metrics-server-9bf64b57-bh6sk                                0/1     Running   0          15
```

Old metrics-server pod metrics-server-8ff8f88c6-87x54 will be deleted automatically.

After certain amount of time, `kubectl get pods -n kube-system` `kubectl get deployments -n kube-system` commands will show running metrics-server.
```shell
kubectl get pods -n kube-system
NAME                                                         READY   STATUS    RESTARTS   AGE
...
metrics-server-9bf64b57-bh6sk                                1/1     Running   0          4m13s
```

```shell
kubectl get deployments -n kube-system
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
coredns          2/2     2            2           2d2h
metrics-server   1/1     1            1           54m
```

Now we can use kubectl top pod command.
```shell
kubectl top pod
NAME                          CPU(cores)   MEMORY(bytes)
php-apache-5b56f9df94-ksp5c   1m           13Mi
```

When metrics-server was not edited appropriately with right config (`- --kubelet-insecure-tls`), resource(CPU) utilization was not available.
```shell
kubectl get hpa
NAME         REFERENCE               TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
php-apache   Deployment/php-apache   <unknown>/50%   1         10        1          8m51
```

Now, it becomes able to monitor the resource utilization of running pods since metrics-server was added and also is able to monitor the resource usage.
```shell
kubectl get hpa
NAME         REFERENCE               TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
php-apache   Deployment/php-apache   0%/50%    1         10        1          147m
```

### Chagne metrics-server metric-resolution configuration
metric-resolution: metrics scraping inteval (default: 15s)
the shortest possible interval: 10s

```shell
kubectl edit deployments.apps metrics-server -n kube-system
```
search `metric-resolution` field.
change to 10s.

---

## kubectl cp & docker cp
#### Copying file from host to one of kind-node.

#### Copying file from one of kind-node to pod.

#### Copying file from host to pod.

---
### `kubectl autoscale` subcommand

`kubectl autoscale deployment php-apache --cpu-percent=50 --min=1 --max=10`
https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/#create-horizontal-pod-autoscaler

The following command lets you edit the config for a specific hpa. For example hpa for php-apache that was created.
`kubectl edit hpa`
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  creationTimestamp: "2023-03-16T01:11:29Z"
  name: php-apache
  namespace: default
  resourceVersion: "357089"
  uid: c0830737-6c3d-4186-b395-c1e2f3e530fd
spec:
  maxReplicas: 10
  metrics:
  - resource:
      name: cpu
      target:
        averageUtilization: 50
        type: Utilization
...
```

---
### Create kind cluster
**Specify Kubernetes version for KinD cluster**
We want to use v1.24.10 k8s version for reproducing the failure cases. You need to specify the k8s version in the file which will be used to create kind cluster.

You can find the docker image names here.
https://github.com/kubernetes-sigs/kind/releases
1.24 image
>1.24: kindest/node:v1.24.7@sha256:577c630ce8e509131eab1aea12c022190978dd2f745aac5eb1fe65c0807eb315

**Reference**
https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/
https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#autoscale

**Simple cluster config**
It has one control plane node and two worker nodes.
You have to specify the image for each node to install the particular kubernetes version. Otherwise, it will just automatically install the latest stable kubernetes version that is supported by kind. You don't specify image for control-plane node.
```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
    image: kindest/node:v1.24.7@sha256:577c630ce8e509131eab1aea12c022190978dd2f745aac5eb1fe65c0807eb315
  - role: worker
    image: kindest/node:v1.24.7@sha256:577c630ce8e509131eab1aea12c022190978dd2f745aac5eb1fe65c0807eb315
```

**Command to create kind cluster with config file**
```shell
kind create cluster --config ex_k8s_cluster.yaml --name [cluster-name]
```

**Reference**
Official tutorial for configuring kind cluster.
https://kind.sigs.k8s.io/docs/user/configuration/#kubernetes-version

---

### Dump log files
`kubectl describe all --all-namespaces`
`kubectl get all --all-namespaces`
`kubectl get hpa php-apache -o yaml`
~~`kubectl get pods -n kube-system kube-scheduler-three-worker-cluster-control-plane -o yaml`~~

---

## HPA
`kubectl delete hpa [NAME-OF-DEPLOYMENT]`


### kubectl get pods to csv format
`kubectl get pods | tr -s '[:blank:]' ','`


---
### Installing kube-scheduler in kind cluster
Surprisingly, `kube-scheduler` is not installed in kind cluster by default.
~~kind cluster has kube-scheduler. Otherwise, how could you schedule pods!? The thing is I believe `kube-scheduler` is not command line tool.~~
Oh yeah it is command line. 
`kube-scheduler --config <filename>`

---

### Important Notes
-  kindest/node image is not using docker as the container runtime but crictl.
docker ps in a kind node (which is docker container)
`docker: command not found`
crictl ps
```shell
CONTAINER           IMAGE               CREATED             STATE               NAME                      ATTEMPT             POD ID              POD
372a01050ae81       d6e3e26021b60       2 hours ago         Running             kindnet-cni               1                   fdf15741cb0e0       kindnet-66vj6
a35422c477edb       5185b96f0becf       2 days ago          Running             coredns                   0                   c5f2d565a65a5       coredns-565d847f94-s2zqw
17126b70d1d73       4c1e997385b8f       2 days ago          Running             local-path-provisioner    0                   184403452b83f       local-path-provisioner-684f458cdd-zh4p7
4d28d751f4260       5185b96f0becf       2 days ago          Running             coredns                   0                   ee5964f3f38ee       coredns-565d847f94-jjqv8
7a5911f83d38b       d6e3e26021b60       2 days ago          Exited              kindnet-cni               0                   fdf15741cb0e0       kindnet-66vj6
bf9e1777d718a       86063cd68dfc9       2 days ago          Running             kube-proxy                0                   67791078589e1       kube-proxy-9lgbs
a1b6ea3a925f7       a8a176a5d5d69       2 days ago          Running             etcd                      0                   d9fb0df7f2374       etcd-three-worker-cluster-control-plane
a6073e2489dab       5225724a11400       2 days ago          Running             kube-scheduler            0                   52123ed046ff0       kube-scheduler-three-worker-cluster-control-plane
d9a5886f2565d       580dca99efc3b       2 days ago          Running             kube-controller-manager   0                   d8a01b1b04776       kube-controller-manager-three-worker-cluster-control-plane
a0f194ae57c93       4bc1b1e750e34       2 days ago          Running             kube-apiserver            0                   f8deeb74bcfa5       kube-apiserver-three-worker-cluster-control-plane
```

---

### Debugging Kubernetes nodes with crictl (kind cluster uses crictl for container management. It does not use docker.)
https://kubernetes.io/docs/tasks/debug/debug-cluster/crictl/

----

### ADDED INFO HOW TO SETUP MOUNT POINTS
Note that I'm using /var/log/pods instead of /var/log/containers/ - it is because on the cluster created by kind Kubernetes containers directory has only symlinks to logs in pod directory.

Save this yaml, for example as cluster-with-extra-mount.yaml , then create a cluster using this (create a directory /tmp/logs before applying this command!):

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  # add a mount from /path/to/my/files on the host to /files on the node
  extraMounts:
  - hostPath: /tmp/logs/
    containerPath: /var/log/pods
    # optional: if set, the mount is read-only.
    # default false
    readOnly: false
    # optional: if set, the mount needs SELinux relabeling.
    # default false
    selinuxRelabel: false
    # optional: set propagation mode (None, HostToContainer or Bidirectional)
    # see https://kubernetes.io/docs/concepts/storage/volumes/#mount-propagation
    # default None
    propagation: Bidirectional
```

`kind create cluster --config=/tmp/cluster-with-extra-mount.yaml`
**Then all containers logs will be in /tmp/logs on your VM.**

https://stackoverflow.com/questions/68933251/kind-kubernetes-cluster-doesnt-have-container-logs

---
### load-generator
kubectl run -i --tty load-generator --rm --image=busybox:1.28 --restart=Never -- /bin/sh -c "while sleep 0.01; do wget -q -O- http://php-apache; done"
https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/#increase-load

---
### Installing Descheduler

1. Install `kustomize`
   1. Go to https://kubectl.docs.kubernetes.io/installation/kustomize/binaries/
   2. You can find this command to install kustomize precompiled binary.
      - `curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"  | bash`
   3. mv kustomize /usr/local/bin
   4. check `kustomize`
2. Run `descheduler` as a deployment.
   - `kustomize build 'github.com/kubernetes-sigs/descheduler/kubernetes/deployment?ref=v0.26.0' | kubectl apply -f -`
    installation output log
      ```shell
      serviceaccount/descheduler-sa created
      clusterrole.rbac.authorization.k8s.io/descheduler-cluster-role created
      clusterrolebinding.rbac.authorization.k8s.io/descheduler-cluster-role-binding created
      configmap/descheduler-policy-configmap created
      deployment.apps/descheduler created
      ```
You can see descheduler pod.
```shell
kubectl get pods --namespace kube-system

NAME                                                         READY   STATUS    RESTARTS        AGE
coredns-565d847f94-jjqv8                                     1/1     Running   0               8d
coredns-565d847f94-s2zqw                                     1/1     Running   0               8d
descheduler-74b6dc9649-8bw22                                 1/1     Running   0               16m
...
```

Since we run it as a deployment, you can find it in deployment as well.
```shell
kubectl get deploy --namespace kube-system

NAME             READY   UP-TO-DATE   AVAILABLE   AGE
coredns          2/2     2            2           8d
descheduler      1/1     1            1           20m
metrics-server   1/1     1            1           6d
```

Open configmap of descheduler
```shell
kubectl get configmap -n kube-system | grep descheduler

NAME                                 DATA   AGE
coredns                              1      8d
descheduler-policy-configmap         1      15h
extension-apiserver-authentication   6      8d
kube-proxy                           2      8d
kube-root-ca.crt                     1      8d
kubeadm-config                       1      8d
kubelet-config                       1      8d
```

```shell
kubectl edit configmap -n kube-system descheduler-policy-configmap
```

**Get descheduler log**

```shell
```
```shell
kubectl logs -n kube-system [deschduler pod name] &> [log file name]

kubectl logs -n kube-system descheduler-74b6dc9649-d7znz &> descheduler.log
```

---
## Taint & Toleration
### How to add and remove taint.
How to add
```shell
kubectl taint nodes three-worker-cluster-worker key1=value1:NoExecute
```
```shell
kubectl taint nodes three-worker-cluster-worker key1=value1:NoSchedule
```

Check if the taint is applied or not.
```shell
kubectl describe node three-worker-cluster-worker
```
```shell
Name:               three-worker-cluster-worker
Roles:              <none>
Labels:             beta.kubernetes.io/arch=amd64
                    beta.kubernetes.io/os=linux
                    kubernetes.io/arch=amd64
                    kubernetes.io/hostname=three-worker-cluster-worker
                    kubernetes.io/os=linux
Annotations:        kubeadm.alpha.kubernetes.io/cri-socket: unix:///run/containerd/containerd.sock
                    node.alpha.kubernetes.io/ttl: 0
                    volumes.kubernetes.io/controller-managed-attach-detach: true
CreationTimestamp:  Tue, 14 Mar 2023 00:48:45 +0000
Taints:             key1=value1:NoExecute
                    key1=value1:NoSchedule
...
```

Remove the taint from the node.
```shell
kubectl taint node three-worker-cluster-worker key1=value1:NoSchedule-
> node/three-worker-cluster-worker untainted
```
```shell
kubectl taint node three-worker-cluster-worker key1=value1:NoExecute-
> node/three-worker-cluster-worker untainted
```

```shell
kubectl describe node three-worker-cluster-worker
```
```shell
Name:               three-worker-cluster-worker
Roles:              <none>
Labels:             beta.kubernetes.io/arch=amd64
                    beta.kubernetes.io/os=linux
                    kubernetes.io/arch=amd64
                    kubernetes.io/hostname=three-worker-cluster-worker
                    kubernetes.io/os=linux
Annotations:        kubeadm.alpha.kubernetes.io/cri-socket: unix:///run/containerd/containerd.sock
                    node.alpha.kubernetes.io/ttl: 0
                    volumes.kubernetes.io/controller-managed-attach-detach: true
CreationTimestamp:  Tue, 14 Mar 2023 00:48:45 +0000
Taints:             <none>
...
```

#### How to list taints in all nodes.
```shell
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints --no-headers
```

---
## Custom column print in kubectl
Reference: https://kubernetes.io/docs/reference/kubectl/#custom-columns

Example 
```shell
kubectl get pods -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.nodeName,HOSTIP:.status.hostIP,PHASE:.status.phase,START_TIME:.metadata.creationTimestamp --sort-by=.metadata.creationTimestamp
```
Output
```shell
NAMESPACE            NAME                                         NODE                 HOSTIP       PHASE     START_TIME
kube-system          kube-controller-manager-kind-control-plane   kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:10Z
kube-system          kube-apiserver-kind-control-plane            kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:13Z
kube-system          etcd-kind-control-plane                      kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:13Z
kube-system          kube-scheduler-kind-control-plane            kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:13Z
kube-system          kindnet-5qsnq                                kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:27Z
kube-system          kube-proxy-h9lds                             kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:27Z
local-path-storage   local-path-provisioner-6b84c5c67f-hl8jz      kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:28Z
kube-system          coredns-6d4b75cb6d-lxl4v                     kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:28Z
kube-system          coredns-6d4b75cb6d-qd7c5                     kind-control-plane   172.18.0.2   Running   2023-04-14T00:07:28Z
kube-system          kindnet-mxmhl                                kind-worker3         172.18.0.3   Running   2023-04-14T00:07:47Z
kube-system          kindnet-f9v6g                                kind-worker          172.18.0.4   Running   2023-04-14T00:07:47Z
kube-system          kube-proxy-jgb94                             kind-worker          172.18.0.4   Running   2023-04-14T00:07:47Z
kube-system          kube-proxy-qj9bm                             kind-worker2         172.18.0.5   Running   2023-04-14T00:07:47Z
kube-system          kube-proxy-zvz6f                             kind-worker3         172.18.0.3   Running   2023-04-14T00:07:47Z
kube-system          kindnet-b427z                                kind-worker2         172.18.0.5   Running   2023-04-14T00:07:47Z
default              php-apache-698db99f59-wqdk5                  kind-worker3         172.18.0.3   Running   2023-04-19T22:05:59Z
kube-system          metrics-server-5744bdc4f4-kg8rc              kind-worker2         172.18.0.5   Running   2023-04-20T00:07:42Z
default              php-apache-698db99f59-g42vx                  kind-worker3         172.18.0.3   Running   2023-04-20T00:55:58Z
```

---

The three-worker-cluster-worker is tainted with `key1=value1:NoExecute`.
So the descheduler was not able to evict one of pods running in the same node (three-worker-cluster-worker2) even if it has `RemoveDuplicates` plugin.
```shell
NAME                                READY   STATUS    RESTARTS   AGE     IP             NODE                           NOMINATED NODE   READINESS GATES
nginx-deployment-58df68d8db-9hmpc   1/1     Running   0          8m15s   10.244.1.129   three-worker-cluster-worker2   <none>           <none>
nginx-deployment-58df68d8db-czbvx   1/1     Running   0          8m14s   10.244.2.199   three-worker-cluster-worker3   <none>           <none>
nginx-deployment-58df68d8db-z9czw   1/1     Running   0          8m16s   10.244.2.198   three-worker-cluster-worker3   <none>           <none>
```

Since three-worker-cluster-worker node was untainted, the descheduler terminates (evicts) one of two duplicate pods (z9czw in this case) from the 'three-worker-cluster-worker2' node. A new pod (ng9pk) was created and scheduled to a 'three-worder-cluster-worker' node. It does not violate RemoveDuplicate anymore.
```shell
NAME                                READY   STATUS    RESTARTS   AGE   IP             NODE                           NOMINATED NODE   READINESS GATES
nginx-deployment-58df68d8db-9hmpc   1/1     Running   0          35m   10.244.1.129   three-worker-cluster-worker2   <none>           <none>
nginx-deployment-58df68d8db-czbvx   1/1     Running   0          35m   10.244.2.199   three-worker-cluster-worker3   <none>           <none>
nginx-deployment-58df68d8db-ng9pk   1/1     Running   0          15s   10.244.3.5     three-worker-cluster-worker    <none>           <none>
```

---

```shell
NAME                                READY   STATUS    RESTARTS   AGE   IP             NODE                           NOMINATED NODE   READINESS GATES
nginx-deployment-58df68d8db-6wzkk   1/1     Running   0          52s   10.244.3.6     three-worker-cluster-worker    <none>           <none>
nginx-deployment-58df68d8db-9hmpc   1/1     Running   0          62m   10.244.1.129   three-worker-cluster-worker2   <none>           <none>
nginx-deployment-58df68d8db-czbvx   1/1     Running   0          62m   10.244.2.199   three-worker-cluster-worker3   <none>           <none>
nginx-deployment-58df68d8db-ng9pk   1/1     Running   0          27m   10.244.3.5     three-worker-cluster-worker    <none>           <none>
```

---

### Node label

**How to add node label**
`kubectl label nodes [node_name] [key=value]`
e.g.,
`kubectl label nodes three-worker-cluster-worker lifecycle=spot`

**How to remove node label**
`kubectl label --overwrite nodes [node_name] [tolology_key]-`
key only, no value.

**How to check node labels**
`kubectl get nodes --show-labels`
`kubectl label --list nodes [node_name]`

---
### S2
Descheduler config
```yaml
    strategies:
      "RemovePodsViolatingTopologySpreadConstraint":
         enabled: true
         params:
           includeSoftConstraints: true
      "RemoveDuplicates":
         enabled: false
      "RemovePodsViolatingInterPodAntiAffinity":
         enabled: true
      "RemovePodsViolatingNodeAffinity":
         enabled: false
      "RemovePodsViolatingNodeTaints":
         enabled: false
      "LowNodeUtilization":
         enabled: false
         params:
           nodeResourceUtilizationThresholds:
             thresholds:
               "cpu" : 20
               "memory": 20
               "pods": 20
             targetThresholds:
               "cpu" : 50
               "memory": 50
               "pods": 50
```

Node label
`kubectl label nodes three-worker-cluster-worker lifecycle=spot`
`kubectl label nodes three-worker-cluster-worker2 lifecycle=spot`
`kubectl label nodes three-worker-cluster-worker3 lifecycle=on-demand`

### Logging

#### kubectl get events

```shell
kubectl get events

LAST SEEN   TYPE     REASON              OBJECT                             MESSAGE
2m37s       Normal   Scheduled           pod/php-apache-698db99f59-4mqtv    Successfully assigned default/php-apache-698db99f59-4mqtv to kind-worker2
2m36s       Normal   Pulling             pod/php-apache-698db99f59-4mqtv    Pulling image "registry.k8s.io/hpa-example"
2m36s       Normal   Pulled              pod/php-apache-698db99f59-4mqtv    Successfully pulled image "registry.k8s.io/hpa-example" in 916.531819ms
2m35s       Normal   Created             pod/php-apache-698db99f59-4mqtv    Created container php-apache
2m35s       Normal   Started             pod/php-apache-698db99f59-4mqtv    Started container php-apache
31s         Normal   Killing             pod/php-apache-698db99f59-4mqtv    Stopping container php-apache
2m38s       Normal   SuccessfulCreate    replicaset/php-apache-698db99f59   Created pod: php-apache-698db99f59-4mqtv
33s         Normal   SuccessfulDelete    replicaset/php-apache-698db99f59   Deleted pod: php-apache-698db99f59-4mqtv
33s         Normal   ScalingReplicaSet   deployment/php-apache              Scaled down replica set php-apache-698db99f59 to 1
2m38s       Normal   ScalingReplicaSet   deployment/php-apache              Scaled up replica set php-apache-698db99f59 to 2
29m         Normal   Created             pod/ubuntu-wget-5dc98c99fb-vwl2b   Created container ubuntu-wget
29m         Normal   Started             pod/ubuntu-wget-5dc98c99fb-vwl2b   Started container ubuntu-wget
29m         Normal   Pulled              pod/ubuntu-wget-5dc98c99fb-vwl2b   Container image "gangmuk/ubuntu-wget:v2" already present on machine
```

#### kubelet log
1. Go to the node
   kubectl exec ...
2. Run `journalctl -u kubelet`



#### How to change kube-scheduler log level (verbosity)
1. Go to the control-plane node where kube-scheduler is running.
    `docker exec -it kind-control-plane /bin/bash`
2. Open the kube-scheduler yaml file.
    `vi /etc/kubernetes/manifest/kube-scheduler.yaml`
3. Add - --v=10 under spec.containers.command
    ```yaml
    ...
    spec:
      containers:
      - command:
        - kube-scheduler
        - --authentication-kubeconfig=/etc/kubernetes/scheduler.conf
        - --authorization-kubeconfig=/etc/kubernetes/scheduler.conf
        - --bind-address=127.0.0.1
        - --kubeconfig=/etc/kubernetes/scheduler.conf
        - --leader-elect=true
        - --v=10 (Add this lijne or change the verbosity field from 1 to 10 if it exists)
    ...
    ```

##### Expected scheduler log output
```shell
10108 2023-03-16T21:40:45.056374564Z stderr F I0316 21:40:45.056205       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="PodTopologySpread" node="three-worker-cluster-worker2" score=200
10109 2023-03-16T21:40:45.056396782Z stderr F I0316 21:40:45.056255       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="PodTopologySpread" node="three-worker-cluster-worker3" score=200
10110 2023-03-16T21:40:45.056408938Z stderr F I0316 21:40:45.056281       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="InterPodAffinity" node="three-worker-cluster-worker2" score=0
10111 2023-03-16T21:40:45.056476955Z stderr F I0316 21:40:45.056304       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="InterPodAffinity" node="three-worker-cluster-worker3" score=0
10112 2023-03-16T21:40:45.056559699Z stderr F I0316 21:40:45.056328       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="NodeResourcesBalancedAllocation" node="three-worker-cluster-worker2" score=99
10113 2023-03-16T21:40:45.056644767Z stderr F I0316 21:40:45.056406       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="NodeResourcesBalancedAllocation" node="three-worker-cluster-worker3" score=99
10114 2023-03-16T21:40:45.056709653Z stderr F I0316 21:40:45.056505       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="ImageLocality" node="three-worker-cluster-worker2" score=0
10115 2023-03-16T21:40:45.056748881Z stderr F I0316 21:40:45.056557       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="ImageLocality" node="three-worker-cluster-worker3" score=0
10116 2023-03-16T21:40:45.05681454Z stderr F I0316 21:40:45.056649       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="TaintToleration" node="three-worker-cluster-worker2" score=300
10117 2023-03-16T21:40:45.056884572Z stderr F I0316 21:40:45.056711       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="TaintToleration" node="three-worker-cluster-worker3" score=300
10118 2023-03-16T21:40:45.056902293Z stderr F I0316 21:40:45.056748       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="NodeAffinity" node="three-worker-cluster-worker2" score=0
10119 2023-03-16T21:40:45.057131975Z stderr F I0316 21:40:45.056882       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="NodeAffinity" node="three-worker-cluster-worker3" score=0
10120 2023-03-16T21:40:45.057165912Z stderr F I0316 21:40:45.056960       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="NodeResourcesFit" node="three-worker-cluster-worker2" score=90
10121 2023-03-16T21:40:45.057187133Z stderr F I0316 21:40:45.056993       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="NodeResourcesFit" node="three-worker-cluster-worker3" score=95
10122 2023-03-16T21:40:45.057203532Z stderr F I0316 21:40:45.057014       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="VolumeBinding" node="three-worker-cluster-worker2" score=0
10123 2023-03-16T21:40:45.057250197Z stderr F I0316 21:40:45.057101       1 schedule_one.go:646] "Plugin scored node for pod" pod="default/load-generator" plugin="VolumeBinding" node="three-worker-cluster-worker3" score=0
10124 2023-03-16T21:40:45.057293388Z stderr F I0316 21:40:45.057194       1 schedule_one.go:704] "Calculated node's final score for pod" pod="default/load-generator" node="three-worker-cluster-worker2" score=689
10125 2023-03-16T21:40:45.057329374Z stderr F I0316 21:40:45.057218       1 schedule_one.go:704] "Calculated node's final score for pod" pod="default/load-generator" node="three-worker-cluster-worker3" score=694
```

**Print log**
Print log since the last 10 second (5 minutes, 1 hour).
```shell
kubectl logs podname-xxxxxxxx-xxxx --since 10s
kubectl logs podname-xxxxxxxx-xxxx --since 5m
kubectl logs podname-xxxxxxxx-xxxx --since 1h
```

**kube-scheduler log path**
```shell
/var/log/pods/kube-system_kube-scheduler-three-worker-cluster-control-plane_0229b65a8525ca77b1cd3075a07fc941/kube-scheduler/0.log
```

**log file ≠ kubectl logs -n kube-system pods/kube-scheduler-three-worker-cluster-control-plane**
Interestingly, kube-scheduler log found in the log file path is not identical to log printed by kubectl log command.
log file is subject to the verbosity level set in kube-scheduler config. However, kubectl logs does not seem to be subject to the verbosity config. At least kubectl logs includes actual pod scheduling log.

---

## Apply linux tc to a pod.
**Goal: Make the metrics-server cannot reach a specific pod so it calculates the wrong average CPU utilization.**
TL;DR
**`tc` command cannot stop metrics-server from getting the CPU utilization telemetry from that pod.**

If the pod does not have `NET_ADMIN` capability, you are not able to run `tc` command. You will see the error.
```shell
RTNETLINK answers: Operation not permitted
```

To use `tc` command inside pod. You have to add `NET_ADMIN` capability. `securityContext` should be under `spec.template.spec.container`.
This is **deployment** yaml file. Again it is not pod yaml config.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: php-apache
spec:
  replicas: 2
  selector:
    matchLabels:
      run: php-apache
  template:
    metadata:
      labels:
        run: php-apache
    spec:
      containers:
      - name: php-apache
        image: registry.k8s.io/hpa-example
        securityContext:
            capabilities:
              add:
                - NET_ADMIN
```

Now pods belonging to this deployment can run `tc` command.

#### How to get the name and the ip of a specific pod.

To specify a pod, you need to know the label of the target pod.

We have two php-apache pod.
```shell
kubectl get pods -o wide
NAME                          READY   STATUS    RESTARTS   AGE   IP             NODE                           NOMINATED NODE   READINESS GATES
php-apache-55d8b696c9-fj7q2   1/1     Running   0          22s   10.244.3.52    three-worker-cluster-worker    <none>           <none>
php-apache-55d8b696c9-zmwtt   1/1     Running   0          22s   10.244.1.159   three-worker-cluster-worker2   <none>           <none>
```

As an example, let's check the yaml config file of the first php-apache pod. To see the current config, run the following command.
```shell
kubectl edit pod php-apache-55d8b696c9-fj7q2
```

You can find the `labels` under `metadata.labels`.
```yaml
apiVersion: v1
kind: Pod
metadata:
  creationTimestamp: "2023-04-03T17:22:17Z"
  generateName: php-apache-55d8b696c9-
  labels:
    pod-template-hash: 55d8b696c9
    run: php-apache
  name: php-apache-55d8b696c9-fj7q2
  namespace: default
  ...
spec:
  containers:
  - image: registry.k8s.io/hpa-example
    ...
    securityContext:
      capabilities:
        add:
        - NET_ADMIN
    ...
status:
  ...
  hostIP: 172.18.0.5
  phase: Running
  podIP: 10.244.3.52
  ...
```


php-apache pod has two key-value pairs for this pod. Different pods have different number of pairs of key-value label. Now we are ready to select this pod specifically.
`-l=....` part finds the pod with that label.
In this case, I don't include the first label which is `pod-template-hash: 55d8b696c9` but you can by simply giving two labels. `-l=run=php-apache,pod-template-hash=55d8b696c9`.
```shell
php_pod_ip=$(kubectl get pod $(kubectl get pods -l=run=php-apache -o jsonpath='{.items[0].metadata.name}') -o jsonpath='{.status.podIP}')
```

The most inner part.
```shell
kubectl get pods -l=run=php-apache -o jsonpath='{.items[0].metadata.name}'
php-apache-55d8b696c9-fj7q2
```
You can get the second pod name by changing the index of items[*].
```shell
kubectl get pods -l=run=php-apache -o jsonpath='{.items[1].metadata.name}'
php-apache-55d8b696c9-zmwtt
```

The outer part.
```shell
kubectl get pod $(kubectl get pods -l=run=php-apache -o jsonpath='{.items[0].metadata.name}') -o jsonpath='{.status.podIP}'
```
is equal to 
```shell
kubectl get pod php-apache-55d8b696c9-fj7q2 -o jsonpath='{.status.podIP}'
10.244.3.52
```
The pod ip is under `status.podIP`.

It returns the pod ip which is what we want!

#### linux tc command

```shell
# delete existing qdisc rules
kubectl exec --stdin --tty pod/${php_pod_name} -- tc qdisc del dev eth0 root;

# add 50ms network delay outgoing from the specific php_pod to metrics_server_pod_ip
kubectl exec --stdin --tty pod/${php_pod_name} -- tc qdisc add dev eth0 root handle 1: prio;
kubectl exec --stdin --tty pod/${php_pod_name} -- tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dst ${metrics_server_pod_ip} flowid 2:1;
kubectl exec --stdin --tty pod/${php_pod_name} -- tc qdisc add dev eth0 parent 1:1 handle 2: netem delay 50ms;

# 100% packet loss outgoing from the specific php_pod.
# kubectl exec --stdin --tty pod/${php_pod_name} -- tc qdisc add dev eth0 parent 1:1 handle 2: netem loss 100%;
```

You can run command inside a specific pod by running `kubectl exec --stdin --tty -- [command]`.

**However, at the end of the day `tc` command fails to stop metrics-server from getting the CPU utilization telemetry from that pod.**

---

### How to delete the network interface of a docker container

Check network interface.
`ip address`
Remember node in kind-cluster is docker container.

This is an example of network interface of kind worker node.

```shell
$ docker exec three-worker-cluster-worker2 ip address

1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
15: eth0@if16: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default
    link/ether 02:42:ac:12:00:06 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 172.18.0.6/16 brd 172.18.255.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fc00:f853:ccd:e793::6/64 scope global nodad
       valid_lft forever preferred_lft forever
    inet6 fe80::42:acff:fe12:6/64 scope link
       valid_lft forever preferred_lft forever
24: veth7237c85f@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default
    link/ether 9a:4d:cd:3b:d4:0e brd ff:ff:ff:ff:ff:ff link-netns cni-75bcde94-0355-a9bb-6a23-5a9e65926046
    inet 10.244.1.1/32 scope global veth7237c85f
       valid_lft forever preferred_lft forever
160: vetha08b96db@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default
    link/ether 3a:2d:cc:77:da:54 brd ff:ff:ff:ff:ff:ff link-netns cni-0aac6dd9-0348-baa6-476e-bad55d4f1b61
    inet 10.244.1.1/32 scope global vetha08b96db
       valid_lft forever preferred_lft forever
```
We have four network interfaces, `lo`, `eth0`, `veth7237c85f`, `vetha08b96db`.

To make the node unreachable, we deleted the specific ip address, 172.18.0.5/16 from the `eth0` interface in the node.
```shell
docker exec three-worker-cluster-worker ip address del 172.18.0.5/16 dev eth0
```
However, the node was still reachable. Meaning, we can find the node `Ready` when we run `kubectl get nodes` command.

As a second trial, I deleted the `eth0` interface,
```shell
docker exec three-worker-cluster-worker ip link delete eth0
```

However, the node was still reachable. Meaning, we can find the node `Ready` when we run `kubectl get nodes` command.


As a third trial, I deleted the next interface, `veth7238c85f`. 
```shell
docker exec three-worker-cluster-worker ip link delete veth9f6df54a
```

Then the status of this node become `NotReady`.
```shell
kubectl get nodes
NAME                                 STATUS     ROLES           AGE   VERSION
three-worker-cluster-control-plane   Ready      control-plane   22d   v1.25.3
three-worker-cluster-worker          NotReady   <none>          22d   v1.25.3
three-worker-cluster-worker2         Ready      <none>          22d   v1.25.3
three-worker-cluster-worker3         Ready      <none>          22d   v1.25.3
```

We found an interesting thing. The new pod was created and scheduled in another healthy node but the pod running in that this node falls in the infinite `Terminating` status.

```shell
$ kubectl get pods -o wide

NAME                          READY   STATUS        RESTARTS   AGE    IP             NODE                           NOMINATED NODE   READINESS GATES
php-apache-55d8b696c9-9x2lt   1/1     Running       0          23h    10.244.2.237   three-worker-cluster-worker3   <none>           <none>
php-apache-55d8b696c9-fj7q2   1/1     Terminating   0          2d4h   10.244.3.52    three-worker-cluster-worker    <none>           <none>
php-apache-55d8b696c9-zmwtt   1/1     Running       0          2d4h   10.244.1.159   three-worker-cluster-worker2   <none>           <none>
```

And kube-system namespace pods running in that nodes are still running and not terminated for some reason.
```shell
$ kubectl get pods -n kube-system -o wide

NAME                                                         READY   STATUS    RESTARTS      AGE   IP            NODE                                 NOMINATED NODE   READINESS GATES
coredns-565d847f94-jjqv8                                     1/1     Running   0             22d   10.244.0.3    three-worker-cluster-control-plane   <none>           <none>
kindnet-77bh2                                                1/1     Running   2 (23h ago)   22d   172.18.0.5    three-worker-cluster-worker          <none>           <none>
kube-proxy-4zpsm                                             1/1     Running   0             22d   172.18.0.5    three-worker-cluster-worker          <none>           <none>
...
```

I tried to restart the `NotReady` node.
```shell
$ kubectl drain three-worker-cluster-worker --ignore-daemonsets

node/three-worker-cluster-worker cordoned
WARNING: ignoring DaemonSet-managed Pods: kube-system/kindnet-77bh2, kube-system/kube-proxy-4zpsm
evicting pod default/php-apache-55d8b696c9-fj7q2
$ (hanging here)
```
If you look at the log, it says "cordoned" which is different from shutdown. (There is uncordon command that brings the node back.)

Btw, you cannot drain the node without `-ignore-daemonsets` flag because kube-system pods are running in the node. To force the drain, you need that flag.
```shell
$ kubectl drain three-worker-cluster-worker

node/three-worker-cluster-worker already cordoned
error: unable to drain node "three-worker-cluster-worker" due to error:cannot delete DaemonSet-managed Pods (use --ignore-daemonsets to ignore): kube-system/kindnet-77bh2, kube-system/kube-proxy-4zpsm, continuing command...
There are pending nodes to be drained:
 three-worker-cluster-worker
cannot delete DaemonSet-managed Pods (use --ignore-daemonsets to ignore): kube-system/kindnet-77bh2, kube-system/kube-proxy-4zpsm
```

Options for drain command.
```shell
--force[=false]: Continue even if there are pods not managed by a ReplicationController, Job, or DaemonSet.
--grace-period=-1: Period of time in seconds given to each pod to terminate gracefully. If negative, the default value specified in the pod will be used.
--ignore-daemonsets[=false]: Ignore DaemonSet-managed pods.
```


It never completed the drain command and hang there.

I opened another terminal and checked the node stutus and it becomes `NotReady` and `SchedulingDisabled`.
```shell
kubectl get nodes

NAME                                 STATUS                        ROLES           AGE   VERSION
three-worker-cluster-control-plane   Ready                         control-plane   22d   v1.25.3
three-worker-cluster-worker          NotReady,SchedulingDisabled   <none>          22d   v1.25.3
three-worker-cluster-worker2         Ready                         <none>          22d   v1.25.3
three-worker-cluster-worker3         Ready                         <none>          22d   v1.25.3
```

However the pod in the node (php-apache-55d8b696c9-fj7q2) was never deleted and still `Terminating.
```shell
kubectl get pods -o wide

NAME                          READY   STATUS        RESTARTS   AGE    IP             NODE                           NOMINATED NODE   READINESS GATES
php-apache-55d8b696c9-9x2lt   1/1     Running       0          23h    10.244.2.237   three-worker-cluster-worker3   <none>           <none>
php-apache-55d8b696c9-fj7q2   1/1     Terminating   0          2d4h   10.244.3.52    three-worker-cluster-worker    <none>           <none>
php-apache-55d8b696c9-zmwtt   1/1     Running       0          2d4h   10.244.1.159   three-worker-cluster-worker2   <none>           <none>
```

And the kube-system in the node is `Running` which does not make sense at all. It should have been terminated and rescheduled in another node.
```shell
$ kubectl get pods -n kube-system -o wide

NAME                                                         READY   STATUS    RESTARTS      AGE   IP            NODE                                 NOMINATED NODE   READINESS GATES
...
kindnet-77bh2                                                1/1     Running   2 (23h ago)   22d   172.18.0.5    three-worker-cluster-worker          <none>           <none>
kube-proxy-4zpsm                                             1/1     Running   0             22d   172.18.0.5    three-worker-cluster-worker          <none>           <none>
...
```

You can bring the node back by executing `uncordon` command.
```shell
$ kubectl uncordon three-worker-cluster-worker

node/three-worker-cluster-worker uncordoned
```

You can see the node is no long Unschedulable, meaning schedulable.
But anyway this is not what I want. I want to shutdown the NotReady node and create a new one which will replace the shutdown node.
```shell
$ kubectl get nodes

NAME                                 STATUS     ROLES           AGE   VERSION
three-worker-cluster-control-plane   Ready      control-plane   22d   v1.25.3
three-worker-cluster-worker          NotReady   <none>          22d   v1.25.3
three-worker-cluster-worker2         Ready      <none>          22d   v1.25.3
three-worker-cluster-worker3         Ready      <none>          22d   v1.25.3
```

#### drain, cordon, uncordon
1. Drain node
   - This will mark the node as unschedulable and also evict pods on the node.
2. cordon node
   - Mark node as unschedulable.
3. uncordon node
   - Mark node as schedulable again.

Actually drain is not deletion.

So I deleted the node
```shell
$ kubectl delete node three-worker-cluster-worker

node "three-worker-cluster-worker" deleted
```

Now we don't see the `three-worker-cluster-worker` node anymore.
```shell
$ kubectl get nodes

NAME                                 STATUS   ROLES           AGE   VERSION
three-worker-cluster-control-plane   Ready    control-plane   22d   v1.25.3
three-worker-cluster-worker2         Ready    <none>          22d   v1.25.3
three-worker-cluster-worker3         Ready    <none>          22d   v1.25.3
```

The pod `php-apache-55d8b696c9-fj7q2` is also terminated.
```shell
$ kubectl get pods -o wide

NAME                          READY   STATUS    RESTARTS   AGE    IP             NODE                           NOMINATED NODE   READINESS GATES
php-apache-55d8b696c9-9x2lt   1/1     Running   0          24h    10.244.2.237   three-worker-cluster-worker3   <none>           <none>
php-apache-55d8b696c9-zmwtt   1/1     Running   0          2d4h   10.244.1.159   three-worker-cluster-worker2   <none>           <none>
```

Now I want to add a new node to this cluster. However, it is not supported by the KinD.

---

### Creating pod latency

##### When the image was pulled.
It actually takes very long time when the images need to be pulled.
```shell
$ kubectl get pods

NAME                          READY   STATUS              RESTARTS   AGE
php-apache-7654df5976-85crd   0/1     ContainerCreating   0          58s
php-apache-7654df5976-h6gd9   0/1     ContainerCreating   0          58s
php-apache-7654df5976-tpvzd   0/1     ContainerCreating   0          58s

$ kubectl get pods

NAME                          READY   STATUS    RESTARTS   AGE
php-apache-7654df5976-85crd   1/1     Running   0          81s
php-apache-7654df5976-h6gd9   1/1     Running   0          81s
php-apache-7654df5976-tpvzd   1/1     Running   0          81s
```

##### When the image is present locally.
`registry.k8s.io/hpa-example` container takes ~5s to become `Running` status.
```shell
$ kubectl get pods -o wide
NAME                          READY   STATUS              RESTARTS   AGE   IP           NODE           NOMINATED NODE   READINESS GATES
php-apache-79c8455955-6xw8v   1/1     Running             0          5s    10.244.1.7   kind-worker2   <none>           <none>
php-apache-79c8455955-8c6ll   0/1     ContainerCreating   0          5s    <none>       kind-worker3   <none>           <none>
php-apache-79c8455955-97jdw   0/1     ContainerCreating   0          5s    <none>       kind-worker    <none>           <none>
php-apache-79c8455955-lvvl6   0/1     ContainerCreating   0          5s    <none>       kind-worker    <none>           <none>
```


---

### Make the node unreachable by stopping kubelet

```shell
kubectl drain kind-worker3 --ignore-daemonsets
docker exec -it kind-worker3 /bin/bas
systemctl stop kubelet
```

---

### I deleted the kindnet-xxx pod and it is never created again.

```shell

kubectl get pods -n kube-system -o wide

NAME                                         READY   STATUS              RESTARTS      AGE     IP           NODE                 NOMINATED NODE   READINESS GATES
...
kindnet-648zh                                1/1     Running             0             7h9m    172.18.0.4   kind-worker          <none>           <none>
kindnet-ctl8s                                0/1     ContainerCreating   0             4m47s   172.18.0.5   kind-worker2         <none>           <none>
kindnet-f547w                                1/1     Running             0             7h9m    172.18.0.3   kind-worker3         <none>           <none>
kindnet-grx2w                                1/1     Running             1 (81m ago)   7h10m   172.18.0.2   kind-control-plane   <none>           <none>
...
```

Because there is no kindnet pod running in kind-worker2 node, any pod fails to be scheduled to this node.
```shell
$ kubectl get pods -o wide
NAME                          READY   STATUS              RESTARTS   AGE   IP            NODE           NOMINATED NODE   READINESS GATES
php-apache-79c8455955-48bkf   1/1     Running             0          11m   10.244.3.23   kind-worker    <none>           <none>
php-apache-79c8455955-976rd   1/1     Running             0          11m   10.244.2.20   kind-worker3   <none>           <none>
php-apache-79c8455955-kq4xk   0/1     ContainerCreating   0          11m   <none>        kind-worker2   <none>           <none>
```

##### Solution
Go into that node and restart the kubelet.

```shell
docker exec -it kind-worker2 /bin/bash
# systemctl restart systemd-logind
# systemctl restart dbus
systemctl restart kubelet # You only need to restart the kubelet.
# systemctl restart dnsmasq NetworkManager
# systemctl restart atomic-openshift-node.service
```

---
## How to use local docker image in deployment

1. Create your own docker image locally.
  1. Write your own Dockerfile
      ```shell
      FROM ubuntu:18.04

      # ARG delay_to=127.0.0.1

      # WORKDIR /app

      RUN apt-get update && \
          apt-get upgrade && \
          apt-get install software-properties-common -y && \
          apt-get install golang-go iproute2 -y && \
          apt-get install iputils-ping -y && \
          apt-get install wget -y && \
          apt-get install curl -y

      EXPOSE 80

      # COPY go.* ./
      # RUN go mod download
      # COPY *.go ./
      # RUN go build -o /reqrouting-spam

      # CMD [ "/reqrouting-spam" ]
      ``` 
  2. Build a new docker image with Dockerfile
      `docker build -t [image_name]:[image_tag] [directory where the Dockerfile is]`
      ```shell
      docker build -t gangmuk/ubuntu-wget:v1 .
      ```
  3. Login docker hub account in your local shell.
      `docker login --username=gangmuk`
      and end the password.
  4. Tag your image. (optional)
      This is not necessary if you want to use the image name you have now. (the one that you input when doing `docker build`)
      ```shell
      $ docker images
      
      REPOSITORY            TAG       IMAGE ID       CREATED              SIZE
      gangmuk/ubuntu-wget   v2        cbe21b024a04   About a minute ago   624MB
      gangmuk/ubuntu-wget   v1        c274d72e4971   12 hours ago         621MB
      ubuntu-wget           v1        *c274d72e4971*   12 hours ago         621MB
      kindest/node          <none>    99f212a7be2b   5 months ago         950MB
      kindest/node          <none>    d8644f660df0   5 months ago         898MB
      ```
      `docker tag c274d72e4971 gangmuk/ubuntu-wget:v1`
  5. Push the newly built docker image to your docker hub repository.
      `docker push gangmuk/ubuntu-wget:v1`
  6. Put this docker image into `spec.spec.container.image` field in deployment yaml file.
      ```yaml
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: ubuntu-wget
        labels:
          app: ubuntu-wget
      spec:
        replicas: 1
        selector:
          matchLabels:
            app: ubuntu-wget
        template:
          metadata:
            labels:
              app: ubuntu-wget
          spec:
            containers:
            - name: ubuntu-wget
              image: gangmuk/ubuntu-wget:v2 ****
              imagePullPolicy: IfNotPresent
              ...
      ```


---
### No disk space in vm having k8s cluster
I don't know why but kind cluster takes up decent amount of disk space even after scheduler log and kubelet log are all cleared up.

You can delete unused docker images 
https://docs.docker.com/engine/reference/commandline/system_prune/
```bash
docker system prune -a
```

/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs
https://stackoverflow.com/questions/71900937/is-it-possible-to-shrink-the-spaces-of-io-containerd-snapshotter-v1-overlayfs-fo
```bash
crictl rmi --prune
```