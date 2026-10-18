# 02 Running HCX over a long program

A migration that lasts years teaches you things a single cutover weekend never will. These are the habits I'd set up on day one.

## Keep HCX current, but not too current

HCX releases come out often, and many bugs you'll hit have already been fixed for someone else. I settled on upgrading roughly every two months and staying one version behind the latest. That gets you the fixes without being the first to meet a new problem. Upgrades go in the maintenance window, never in the middle of a migration wave, and I compare service mesh status, tunnel status and the list of extended networks before and after.

## Separate network changes from migrations

Stretching or unstretching a network and migrating VMs are different kinds of risk. Do them in different windows. If something goes wrong while you are doing both at once, you lose time working out which change caused it.

## Size service meshes from the data, not the link

A fast Direct Connect doesn't mean fast replication. Each service mesh's tunnel had its own ceiling, around 1.25 Gbps in every version I used, so a big link still moved data at the speed of the mesh. Work out how much data has to move and in what time, then build enough meshes. See [ADR 0003](../adr/0003-size-service-meshes-from-data-volume.md).

## Turn seed checkpoints on

Initial syncs of multi-terabyte VMs can run for days. Without seed checkpoints, a timeout means starting again from zero. With them, the sync resumes where it stopped. I treat them as a default setting, not an option.

## Never let VMs switch over by themselves

By default, a VM can switch over the moment its sync finishes, at any hour, with nobody watching and before firewall or load-balancer changes are live. Every batch should have a scheduled switchover date agreed with the application team, and a window of at least 24 hours between start and end, so slower VMs have time to power on.

## Treat heavy VMs as special cases

Large, busy VMs, usually databases, can time out when switched over in a batch. Move them with replication-assisted vMotion, one at a time, with someone watching. Plan batches by application so a database and its application servers move together. It's more effort, but each VM only migrates once.

## Agree a rollback rule before the window opens

Our windows were six to eight hours. The first two were for finding and reporting problems, and if a problem wasn't fixed by the sixth hour, we rolled back. Deciding that rule in advance means nobody argues about it at 3 a.m. Keep the source copy until the wave is signed off, so rolling back is just powering the original on.

## Know what this doesn't cover

These notes come from VLAN-backed networks on distributed switches. If your VMs sit on NSX overlay networks (VXLAN in NSX-V, overlay segments in NSX-T), check how HCX extends and stages them; you select the NSX-backed network rather than an ordinary port group. NSX Edge services, such as load balancing, NAT, VPN and DHCP, don't move with the VMs and need their own plan.
