# Build vs buy

The prototype in this repository shows how each stage works. Production programs usually run on established products. Verify each product's current capabilities before relying on it.

| Stage | What the prototype shows | Existing products |
| --- | --- | --- |
| Inventory | Schema mapping and data cleaning | RVTools, AWS Application Discovery Service, Azure Migrate discovery |
| Classify and business case | 7R rules and their reasoning | AWS Migration Evaluator, Azure Migrate assessments |
| Target mapping and sizing | Weighted scoring and instance mapping | AWS Migration Evaluator, Azure Migrate, VMware sizing tools |
| Wave planning | Grouping by dependency and environment | AWS Migration Hub, Azure Migrate dependency analysis |
| Security translation | NSX rules to Security Groups or NSGs | No common off-the-shelf tool; usually custom scripts |
| Moving workloads | Runbook generation | VMware HCX, AWS MGN, Azure Migrate, Oracle Cloud Migrations, Migration Toolkit for Virtualization (built on the open-source Forklift), Nutanix Move, virt-v2v |
| AI-assisted migration | Out of scope for v1 | AWS Transform (check current capabilities) |
| IaC | Terraform rendering | Terraform, AWS Control Tower / Landing Zone Accelerator, Azure landing zone modules |

## When to build

- The step is specific to your estate, such as translating NSX firewall rules.
- You need explainable, auditable output that a product does not provide.
- You need to glue several products together through a common schema.

## When to buy

- A mature product already covers the step, such as replication and cutover.
- Vendor support and certification matter more than flexibility.
