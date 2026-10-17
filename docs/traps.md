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
