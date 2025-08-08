"""A distributed queue allows for multiple producers and subscribers.

- Supports queue item dependency
- Atomic writes/reads
- Receives status of jobs returned to support dependencies
- Mostly FIFO
    (concurrent writes have no required FIFO - will not attempt to resolve the race conditions)
- Supports priority values of the queues
"""
