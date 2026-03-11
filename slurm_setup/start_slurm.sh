#!/bin/bash
git clone https://github.com/giovtorres/slurm-docker-cluster.git
cd slurm-docker-cluster
# cp .env.example .env    # optional: edit to change version, enable GPU, etc.

# Option A: Pull pre-built image from Docker Hub (fastest)
docker pull giovtorres/slurm-docker-cluster:latest
docker tag giovtorres/slurm-docker-cluster:latest slurm-docker-cluster:25.11.2

# Option B: Build from source
make build

# Start the cluster
make up
make status             # verify nodes are idle
make test               # run full test suite
make help               # see all available commands