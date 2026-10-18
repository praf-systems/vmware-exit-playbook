# Traps and lessons from the field

Every one of these has cost someone a weekend. Most of them have cost me one. Each trap below is turned into a rule the pipeline enforces, so the next migration doesn't repeat it.

| Trap | What the pipeline does about it |
| --- | --- |
| NSX-V accepts VMs and IPs directly in rules; NSX-T needs groups | The security stage builds groups first, then rules |
| Manual firewall rule translation is slow and error-prone at scale | Translation is automated from an export or API |
| Stretched networks without Mobility Optimized Networking cause traffic tromboning | The cutover runbook requires MON on extended segments |
| Tags, DRS rules, storage policies and folders get forgotten | Inventory captures them; validation checks they exist on the target |
| RVTools column names vary by version; sizes mix MiB and GiB | Inventory maps columns and normalizes units before anything else |
| Templates and powered-off VMs distort sizing | They are flagged separately and moved by cold migration |
| Production moved before the path is proven | The wave planner enforces non-production first |
| Snapshots stop a VM from being staged, and one bad VM fails a whole batch | Inventory flags snapshots from the `vSnapshot` sheet, before batches are built |
| A mounted ISO makes a migration fail with only a generic error | Inventory flags connected media from the `vCD` sheet |
| DRS rules and tags with no matching setup on the destination break the switchover | Inventory captures them; the readiness stage will check they exist on the destination |
| Large, busy VMs time out when switched over in a batch | The wave planner will give memory-heavy VMs their own replication-assisted slot |
| A database moved without its application servers breaks the application | The wave planner will group VMs by application |
| One service mesh caps throughput, however big the network link | Sizing will calculate meshes from data volume (ADR 0003) |
| A failed initial sync restarts from zero | Runbooks set seed checkpoints on by default |
| Stretched networks are left in place for weeks, and latency builds up | The wave planner will move each segment within as few waves as possible |
| VMs switch over on their own as soon as they finish syncing | Runbooks require a scheduled switchover window of at least 24 hours |
| Backups running during a sync break it | Runbooks take VMs out of backup before staging (ADR 0005) |
| Perimeter firewall rules are not ready when the VMs arrive | The readiness stage will treat firewall rules as a migration prerequisite |
| Settings that can't be changed after deployment are sized for today, not for growth | Destination design follows ADR 0004 |
