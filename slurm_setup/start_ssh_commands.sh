#!/bin/bash

# Run in the container to start the ssh server
yum update -y && yum install openssh-server -y
ssh-keygen -A
/usr/sbin/sshd -D
