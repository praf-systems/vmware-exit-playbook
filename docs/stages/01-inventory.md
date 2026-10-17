# Stage 1: Inventory

Turns an RVTools vInfo export into a validated `inventory.json`, the input for every later stage.

## Input

An RVTools export of the **vInfo** sheet, as `.csv` or `.xlsx`. For `.xlsx`, the `vInfo` sheet is used if present, otherwise the first sheet.

## What it does

1. **Maps columns.** RVTools column names differ between versions (`Powerstate` vs `Power State`, `Provisioned MiB` vs `Provisioned MB`). `config/rvtools_columns.yaml` lists the accepted names for each field; matching ignores case and extra spaces. A missing required column stops the run with a message naming every alias that was tried.
2. **Normalizes units.** Sizes are converted to GiB. The unit is read from the column name; `Memory` with no unit is treated as MiB. RVTools labels some columns `MB` although the values are MiB, so both convert the same way.
3. **Cleans values.** Comma-formatted numbers are parsed, blank cells become `null`, and power states are standardized.
4. **Assigns identity.** The VM UUID is used as `vm_id`. If an export has no UUID column, a stable ID is generated from the VM name, datacenter and cluster, and the VM is flagged `generated_id`. Duplicate IDs stop the run.
5. **Flags edge cases** so later stages can treat them differently:

| Flag | Meaning | Why it matters later |
| --- | --- | --- |
| `template` | VM template | Excluded from sizing; rebuilt rather than migrated |
| `powered_off` | Powered off | Candidate for retirement or cold migration |
| `suspended` | Suspended | Needs a decision before migration |
| `missing_os` | No OS reported | Target mapping cannot be automatic |
| `zero_disk` | No provisioned storage | Likely stale record |
| `zero_cpu` | No vCPUs reported | Likely bad data |
| `generated_id` | ID was generated | No UUID in the source |

6. **Validates** the result against `schemas/inventory.schema.json` and writes it.

## Output

`inventory.json` with a source block (file, format and which column fed each field), a summary of totals, and one record per VM. Each record keeps `source_row`, so any result can be traced back to the original export.

## Run it

```bash
exitplaybook-inventory --input samples/rvtools_vinfo_sample.csv --output runs/inventory.json
```

## Extending it

- **A new RVTools version renames a column:** add the new name to `config/rvtools_columns.yaml`. No code change is needed.
- **A different inventory source** (vCenter API, a CMDB export): write a reader that produces the same schema. Every later stage keeps working.
