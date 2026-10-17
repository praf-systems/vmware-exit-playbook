# Sample data

All files here are **synthetic**. Names, UUIDs, hosts and sizes are invented; business units use industry labels only.

| File | Purpose |
| --- | --- |
| `rvtools_vinfo_sample.csv` | Current RVTools column names (MiB). Includes edge cases: a template, powered-off and suspended VMs, a missing OS, a zero-disk VM and a comma-formatted number. |
| `rvtools_vinfo_legacy.csv` | Older column names (`Power State`, `Memory MB`, `Provisioned MB`, VMware Tools OS) and no UUID column, to prove the column mapping and generated IDs. |
