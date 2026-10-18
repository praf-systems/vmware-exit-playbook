# Sample data

All files here are **synthetic**. Names, UUIDs, hosts and sizes are invented; the applications are made up and not based on any real organization.

| File | Purpose |
| --- | --- |
| `rvtools_vinfo_sample.csv` | Current RVTools column names (MiB). Includes edge cases: a template, powered-off and suspended VMs, a missing OS, a zero-disk VM and a comma-formatted number. |
| `rvtools_vinfo_legacy.csv` | Older column names (`Power State`, `Memory MB`, `Provisioned MB`, VMware Tools OS) and no UUID column, to prove the column mapping and generated IDs. |
| `app_tags.csv` | Application owner knowledge for stage 2: application, environment, criticality, owner and explicit strategy decisions (one repurchase, one retain). |
| `powercli_export_sample.csv` | The shape `scripts/export-inventory.ps1` produces (GB and MB columns, PowerCLI power states), to prove stage 1 accepts it. |
| `rvtools_vsnapshot_sample.csv` | The `vSnapshot` sheet: two VMs with snapshots, plus one row for a VM that is no longer in vInfo. |
| `rvtools_vcd_sample.csv` | The `vCD` sheet: one VM with an ISO mounted, and one with an empty drive that must not be flagged. |
