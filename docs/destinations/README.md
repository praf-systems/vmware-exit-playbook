# Destination guides

The pipeline decides **where** each workload should go. These guides cover **what you build there** to receive it.

I'm starting where the least has been written from a migration architect's point of view: open-source virtualization in your own data center, and Oracle Cloud Infrastructure in the cloud. The mainstream clouds get a thin skeleton of shared principles later; plenty is already written about them.

## Status

| Destination | Path | Guide | How it's tested |
| --- | --- | --- | --- |
| OpenShift Virtualization | Leave | In progress | Lab sessions (Red Hat Developer Sandbox, then a self-built KubeVirt lab) |
| Oracle Cloud Infrastructure | Move | Planned | OCI free tier |
| KVM, Proxmox VE, OpenStack | Leave | Planned | Lab |
| AWS, Azure, GCP | Move | Planned: shared-principles skeleton only | Documentation, plus earlier hands-on AWS work |

Every guide opens with one of three labels, updated as testing progresses:

- **Tested in a lab:** everything described was done hands-on.
- **Partly tested:** some sections are from the lab, the rest from documentation.
- **Designed from documentation:** not yet tried hands-on.

None of these guides comes from a production migration, and each one says so. They record what I tested myself, what it cost, and what I'd still verify before doing it for real.

## What every guide covers

So destinations can be compared side by side, each guide answers the same questions in the same order:

1. When this destination is the right choice, and when it isn't
2. How the platform is structured
3. Identity and access
4. Networking and hybrid connectivity
5. IP address planning
6. Security baseline, and how NSX firewall rules translate
7. Storage
8. Migration tooling and staging
9. Backup and disaster recovery
10. Operations and monitoring
11. Cost and licensing, including what the lab cost to run
12. The vendor's own tooling, and when to use it instead of building your own
13. Traps found in the lab
14. What I'd still verify before production

## Concepts across platforms

A starting map of equivalent ideas. The analogies are rough, and each guide explains where they break down.

| Idea | VMware | OpenShift Virtualization | Oracle Cloud Infrastructure | AWS |
| --- | --- | --- | --- | --- |
| Where VMs run | ESXi host | Worker node | Compute instance on a host | EC2 instance on a host |
| Management plane | vCenter | OpenShift console and APIs | OCI console and APIs | AWS console and APIs |
| Grouping for access and policy | Folders and permissions | Projects (namespaces) | Compartments | Accounts and OUs |
| Network | Port group or NSX segment | Pod network, or a secondary network for VLANs | VCN and subnets | VPC and subnets |
| Network hub | NSX Tier-0 gateway | Cluster networking | Dynamic Routing Gateway | Transit Gateway |
| Private link to the data center | n/a | n/a | FastConnect | Direct Connect |
| Firewall between workloads | NSX distributed firewall | Network policies | Security lists and network security groups | Security groups |
| VM disk | VMDK on a datastore | Persistent volume | Block volume | EBS volume |
