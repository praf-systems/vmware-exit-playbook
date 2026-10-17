# Architecture

The playbook is a pipeline of eight stages. Each stage is an independent package that reads one validated input, applies deterministic logic and writes one validated output for the next stage.

## Why a schema-driven pipeline

- **Portability.** Any estate that can be exported into the inventory schema can use the pipeline.
- **Testability.** Each stage can be tested in isolation with synthetic data.
- **Replaceability.** A stage can be swapped for a commercial tool as long as the tool's output is mapped to the same schema. See [build-vs-buy.md](build-vs-buy.md).

See [ADR 0001](adr/0001-schema-driven-stages.md) for the decision record.

## Stage contracts

| # | Stage | Input | Logic | Output | Next consumer |
| --- | --- | --- | --- | --- | --- |
| 1 | Inventory | RVTools export (vInfo, vDisk, vNetwork) or vCenter API | Map version-specific columns to one schema; normalize units; flag templates and powered-off VMs | `inventory.json` | Classify, Sizing |
| 2 | Classify | `inventory.json` + owner and criticality tags | Assign a 7R strategy per VM | `classified.json` | Target mapping |
| 3 | Target mapping | `classified.json` + decision weights | Score each workload against stay, move and leave targets | `targets.json` | Sizing, Wave planning |
| 4 | Sizing | `targets.json` | VM specs to EC2 instance types, or host counts for VMC, EVS or KVM | `sizing.json` + cost estimate | IaC |
| 5 | Wave planning | `targets.json` + dependencies and environments | Group by application and environment, non-production first, within maintenance windows | `waves.json` | Security, Cutover |
| 6 | Security translation | NSX DFW export + migration list | Resolve rule sources, destinations and services to target hosts | `sg_rules.csv` | IaC |
| 7 | IaC generation | `sizing.json`, `sg_rules.csv`, landing zone settings | Render Terraform modules per wave | Terraform plans | Cutover |
| 8 | Cutover and validation | `waves.json` + Terraform state | Generate runbooks, pre-checks, rollback steps and post-migration tests | Runbooks + validation report | Lessons feed back into stage 2 |

## The 7Rs used in stage 2

| Strategy | Meaning |
| --- | --- |
| Retire | Decommission; no longer needed |
| Retain | Keep where it is for now |
| Rehost | Move as-is (lift and shift), e.g. HCX or AWS MGN |
| Relocate | Move the hypervisor-level workload without change, e.g. to VMC or EVS |
| Replatform | Move with light changes, e.g. to a managed database |
| Repurchase | Replace with a SaaS or commercial product |
| Refactor | Re-architect for cloud-native services |

## Data flow principles

- Outputs are written to a run directory, never overwritten in place.
- The same input always produces the same output.
- Every record keeps the source VM identifier, so any result can be traced back to the inventory.
