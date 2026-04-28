#!/bin/bash
mkdir -p /etc/docker
echo '{"storage-driver": "vfs"}' > /etc/docker/daemon.json

dockerd &
sleep 3

docker login ingehack.azurecr.io \
    -u "$ACR_USERNAME" \
    -p "$ACR_PASSWORD"

docker pull ingehack.azurecr.io/challs/screw-cryptography-inner:latest

/usr/sbin/sshd -D -p 6767
