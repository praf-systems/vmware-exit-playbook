# ADR 0003: Size service meshes from data volume

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

Replication throughput in HCX is limited by each service mesh's tunnel, not by the size of the network link underneath it. In the environments I worked in, a mesh delivered around 1.25 Gbps even over a 10 Gbps Direct Connect. Staging too many VMs on one mesh made initial syncs slow enough to time out.

## Decision

The number of service meshes is calculated from the data to be moved and the time available, not chosen up front:

> meshes = data to replicate ÷ (throughput per mesh × efficiency × hours available)

For example, 10 TB over one mesh at 1.25 Gbps takes about 18 hours at full speed, and closer to a day at a realistic 70% efficiency. The throughput figure is measured after the first wave and the plan corrected with real numbers.

## Consequences

- **Positive:** timelines are realistic from the start, and syncs are spread so no single mesh becomes a bottleneck.
- **Negative:** more meshes mean more appliances to deploy, upgrade and monitor.
- **Mitigation:** treat the per-mesh figure as an observation, not a product fact, and check the current limits for your HCX version.
