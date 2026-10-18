# ADR 0005: Agree a temporary RPO for the migration period

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

Backups and migrations clash. A backup that runs while a VM is replicating takes a snapshot the destination copy doesn't know about, and the sync fails. So VMs have to come out of backup while they are being staged and moved, which leaves a gap in protection.

## Decision

The gap is managed openly rather than ignored:

- Take a full backup of each VM a few hours before staging it.
- Remove staged VMs from backup until switchover, keeping waves short and spread across service meshes so the gap stays small.
- Agree a temporary RPO and RTO for the migration period with the business, in writing, before the first wave.
- After switchover, resume backups on the destination (tags work well for this) and confirm a successful backup within 24 hours.
- Keep the source copy out of backup and off the network, so a backup job can never power it back on.

## Consequences

- **Positive:** migrations don't fail because of backup jobs, and the business knows exactly how protected each VM is at every point.
- **Negative:** for the length of each wave, recovery depends on the pre-staging backup.
- **Mitigation:** short waves, and a post-migration check that every moved VM has a fresh backup.
