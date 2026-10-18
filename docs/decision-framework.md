# Decision framework: stay, move or leave

Stage 3 scores each workload against the available paths. The weights live in `config/` so each organization can tune them. The ratings below are starting assumptions to refine, not findings.

| Criterion | Stay: VCF / EVS / VMC / OCVS | Move: OCI | Move: EC2 via MGN | Move: Azure | Leave: OpenShift Virtualization | Leave: KVM / Proxmox / OpenStack |
| --- | --- | --- | --- | --- | --- | --- |
| Change to operations and skills | Low | Medium | Medium | Medium | Medium to high (Kubernetes skills) | High |
| Migration effort and risk | Low | Medium | Medium | Medium | Medium | High |
| Exposure to VMware licensing | Retained | Removed | Removed | Removed | Removed | Removed |
| How the platform is paid for | VMware subscription | Pay per use | Pay per use | Pay per use | Red Hat subscription | Free software; support optional |
| Tooling maturity for the move | High (HCX) | Medium (Oracle's migration service; check current scope) | High (MGN) | High (Azure Migrate) | Medium to high (Migration Toolkit for Virtualization) | Lower (virt-v2v, scripts) |
| Modernization path | Limited | Strong | Strong | Strong | Strong (VMs and containers on one platform) | Limited |
| Data residency and sovereignty control | Depends on where it runs | Region-bound | Region-bound | Region-bound | Full, if self-hosted | Full, if self-hosted |

Staying is a legitimate answer. It can be the safest short-term choice, for example while a contract runs out or when there isn't time to migrate safely. The framework shows the cost of each path openly rather than ruling any of them out.

## How the score is used

1. Each criterion is rated per workload on a 1–5 scale.
2. Ratings are multiplied by the configured weights and summed per path.
3. The highest-scoring path is recommended, together with the two criteria that contributed most and the margin over the next path.
4. If the margin is small, the output flags the workload for human review instead of forcing a choice.

## Questions the framework is designed to answer

- When is staying on VMware, but in a cloud, the lowest-risk option?
- When does the licensing saving outweigh the cost and risk of re-platforming?
- Which workloads should be retired rather than moved?
- Which workloads are good candidates for an open-source hypervisor?
