---
layout: post
title: "Don't mount disk on EC2"
tags: [ec2, disk, mount]
date: 2026-01-03
category: blog
---

<!-- private link to the chat with claude about this issue: [link](https://chatgpt.com/share/67772393-802b-8008-9810-09670551658a) -->

# Don't mount disk on EC2

I had an AWS EC2 g6e instance that became completely inaccessible after a stop/start cycle. SSH refused connections with "Connection refused", SSM reported "TargetNotConnected", and EC2 Instance Connect failed with access denied. The instance showed as running in the console but was unreachable through any method.
The system console logs showed what was happening during boot:

```text
[TIME] Timed out waiting for device dev-disk-by-uuid-9714e0b6-5aae-4f32-9745-c13988589b52
[DEPEND] Dependency failed for mnt-data.mount - /mnt/data
[DEPEND] Dependency failed for local-fs.target - Local File Systems
You are in emergency mode.
```

The boot process was waiting for a device with UUID 9714e0b6-5aae-4f32-9745-c13988589b52, timing out after 90 seconds, then dropping into emergency mode. In emergency mode, network services like SSH and SSM never start, which is why the instance was unreachable.

The day before, I had mounted the instance's NVMe instance store drive to /mnt/data and added this line to /etc/fstab:
```text
UUID=9714e0b6-5aae-4f32-9745-c13988589b52 /mnt/data ext4 defaults 0 0
```
The problem is that instance store drives are ephemeral storage physically attached to the host machine. When you stop and start an EC2 instance (not reboot), the instance may move to a different physical host. When this happens, the instance store is erased and you get a new empty drive, potentially with a different UUID. A reboot keeps the instance on the same host and preserves the instance store, but stop/start does not. The UUID from yesterday's filesystem no longer existed, so the boot process waited for a device that would never appear.

# The Fix

Since I couldn't access the instance, I needed to edit /etc/fstab offline. The approach: stop the instance, detach its root EBS volume, attach the volume to a temporary instance, mount it and edit the fstab, then reattach it to the original instance. This works because EBS volumes are network-attached storage that can be moved between instances.

Stop the instance and detach the root volume:
```text
aws ec2 stop-instances --instance-ids i-0d2c5421529035454 --region us-east-1
aws ec2 wait instance-stopped --instance-ids i-0d2c5421529035454 --region us-east-1
aws ec2 detach-volume --volume-id vol-04e78a1504e7346f5 --region us-east-1 --force
```

Create a temporary t3.micro instance in the same availability zone and attach the broken volume:

```text
aws ec2 run-instances \
  --image-id ami-0e2c8caa4b6378d8c \
  --instance-type t3.micro \
  --key-name eks-nodes-east \
  --subnet-id subnet-02963b40119f781a4 \
  --region us-east-1

aws ec2 attach-volume \
  --volume-id vol-04e78a1504e7346f5 \
  --instance-id i-0c2c42e6157f9444e \
  --device /dev/sdf \
  --region us-east-1
```


SSH into the temporary instance and fix the fstab:

```text
ssh -i [path_to_pem_file] [username]@[temp-ec2-instance-public-ip]

sudo mkdir /mnt/fix
sudo mount /dev/xvdf1 /mnt/fix  # or /dev/nvme1n1p1 depending on instance type
sudo vi /mnt/fix/etc/fstab

# Deleted the line: UUID=9714e0b6-5aae-4f32-9745-c13988589b52 /mnt/data ext4 defaults 0 0
sudo umount /mnt/fix
```
Detach the volume from the temporary instance and reattach to the original instance:

```text
aws ec2 detach-volume --volume-id vol-04e78a1504e7346f5 --region us-east-1

aws ec2 wait volume-available --volume-ids vol-04e78a1504e7346f5 --region us-east-1

aws ec2 attach-volume \
  --volume-id vol-04e78a1504e7346f5 \
  --instance-id i-0d2c5421529035454 \
  --device /dev/sda1 \
  --region us-east-1

aws ec2 start-instances --instance-ids i-0d2c5421529035454 --region us-east-1
```

The instance booted successfully. The new system log showed:

```text
[[OK]] Reached target local-fs.target - Local File Systems.
[[OK]] Reached target multi-user.target - Multi-User System.
[[OK]] Reached target graphical.target - Graphical Interface.
Ubuntu 24.04.3 LTS ip-172-31-17-22 ttyS0
```

## Why This Works

EBS volumes are network-attached storage that exist independently of EC2 instances. The hypervisor presents them as local block devices to the guest OS (like /dev/nvme0n1 or /dev/xvda), but they're actually accessed over the network. This separation of compute and storage allows you to detach an EBS volume from one instance and attach it to another, which is impossible with physical hardware where the root drive is physically inside the machine.

Instance store drives are different - they're actual NVMe SSDs physically installed in the host server. They're faster because there's no network hop, but they're tied to that specific physical host. When an instance stops, the data is erased and the instance may start on a different host with different instance store drives.

The correct way to use instance store in /etc/fstab is with the "nofail" option:

```text
/dev/nvme1n1  /mnt/data  ext4  defaults,nofail  0  2
```

The "nofail" option tells the system to continue booting even if the device is missing. Without it, a missing device causes the boot to fail and drop into emergency mode. Alternatively, don't put instance store in fstab at all and mount it via a startup script that formats it fresh on each boot.