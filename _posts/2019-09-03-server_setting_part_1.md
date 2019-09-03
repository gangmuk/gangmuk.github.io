---
title: "Server setting part 1 - montblanc"
date: 2019-09-03 17:27:28 -0400
categories: ubuntu server setting
---

prerequisite
  ubuntu 18.04 LTS
  private ip
  
- ip change
  ```bash
  cd /etc/netplan
  vi xxx.yaml
  ```
  
  - example file (montblanc server)
  ```bash
  network:
    version: 2
    renderer: networkd
    ethernets:
      eno1:
        dhcp4: no
        dhcp6: no
        addresses: [ip/port]
        gateway4: gateway
        nameservers:
                addresses: [dns1, dns2]
    ```
  ```bash
  netplan apply
  ```
- disk mount
  ```bash
  mkdir /mnt/data1
  mnt /mnt/data1
  ```
- create an account
  - login to account having root authentication
  ```bash
  sudo adduser gangmuk
  ```
  ```bash
  gpasswd -a gangmuk sudo
  ```
  - delete an account and its home directory
  ```bash
  sudo userdel -rf gangmuk
  ```
- basic application installation
  - zsh
    - install
      ```bash
      sudo apt-get install zsh
      ```
    - default login shell change
      ```bash
      chsh
      /bin/zsh
      ```
    - default setting
      -press (2)
  - Oh My Zsh 
    - install
    ```bash
    curl -L https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh | sh
    ```
    - 
    
  -tmux
    - install
      ```bash
      sudo apt-get install tmux
      ``` 
      - backup original tmux setting file 
      (if you haven't set your own tmux setting file, then there is no default tmux setting file)
      ```bash
      mkdir /home/gangmuk/backup
      cp 
      ```
  - 
    
    
    
    
    
    
    
    
