# Decision framework: stay, move or leave

Stage 3 scores each workload against the available paths. The weights live in `config/` so each organization can tune them. The ratings below are starting assumptions to refine, not findings.

| Criterion | Stay: EVS / VMC | Move: EC2 via MGN | Move: Azure | Leave: KVM / CloudStack |
| --- | --- | --- | --- | --- |
| Change to operations and skills | Low | Medium | Medium | High |
| Migration effort and risk | Low | Medium | Medium | High |
| Exposure to VMware licensing | Retained | Removed | Removed | Removed |
| Tooling maturity for the move | High (HCX) | High (MGN) | High (Azure Migrate) | Lower (virt-v2v, scripts) |
| Modernization path | Limited | Strong | Strong | Limited |
| Data residency and sovereignty control | Region-bound | Region-bound | Region-bound | Full, if self-hosted |

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
