# 01 Getting the inventory

Every migration I've worked on started the same way: someone asks "how big is it?", and nobody has a number they trust. The first real job is getting an inventory you can stand behind.

## My first choice: RVTools

RVTools is free, read-only and quick, and most VMware teams already know it. My routine:

1. **Use a read-only account.** Ask for a dedicated vCenter account with the read-only role. It's an easy yes for the VMware team, and it means nobody has to worry about what the tool might change.
2. **Export every vCenter, not just the main one.** There is always a second vCenter: the DR site, the lab that quietly became production, the one an acquisition brought in. Ask for the full list before you start.
3. **Export to Excel and keep the whole workbook.** Stage 1 only reads the `vInfo` sheet, but `vDisk`, `vNetwork` and `vHost` become useful later for sizing and network planning.
4. **Date the files.** `rvtools-<vcenter>-2026-10-17.xlsx`. You will export again before every wave, and you will want to compare.
5. **Treat it as a snapshot.** An inventory is out of date the day after you pull it. Plan to re-export before each migration wave.

## When RVTools isn't allowed: PowerCLI

Some security teams won't approve installing RVTools on a jump host. PowerCLI is usually already approved, because the VMware team uses it every day. [`scripts/export-inventory.ps1`](../../scripts/export-inventory.ps1) produces a CSV with column names stage 1 already understands, so the rest of the pipeline doesn't care which tool you used.

```powershell
./scripts/export-inventory.ps1 -Server vcenter.example.local -OutFile inventory-export.csv
exitplaybook-inventory --input inventory-export.csv --output runs/inventory.json
```

Two choices in that script worth knowing about:

- **It uses the instance UUID, not the BIOS UUID.** Cloned VMs can end up sharing a BIOS UUID, and stage 1 rightly refuses duplicate IDs. The instance UUID is unique within a vCenter.
- **It exports templates separately.** `Get-VM` doesn't return templates, so the script adds them with `Get-Template`. Forgetting templates is an easy way to under-count storage.

## What I'd avoid: querying the vCenter database

It is tempting to go straight to the vCenter database for a "complete" export. I wouldn't. It isn't a supported interface, the schema changes between versions, and you are poking at the database a production management plane depends on. Everything you need is available through RVTools, PowerCLI or the vCenter API.

## Allocated is not used

An inventory shows what each VM was **given**: vCPUs, memory, provisioned disk. It doesn't show what the VM actually **uses**. For right-sizing, pull utilization history from your monitoring platform (Aria Operations, if you have it) over at least 30 days, including a month-end. Migrating allocation instead of usage is how cloud bills end up larger than the data center they replaced.
