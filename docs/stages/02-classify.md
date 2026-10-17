# Stage 2: Classify

Assigns each VM one of the 7R strategies, with the reasons behind it, a confidence level and a flag when a person should check the result.

## Inputs

- `inventory.json` from stage 1. It is validated against the inventory schema before anything else; an invalid file stops the run.
- An optional **tags** CSV (`samples/app_tags.csv`) with application owner knowledge: `vm_name, application, environment, criticality, owner, decision, notes`. Values are checked; a misspelled strategy or a tag for a VM that is not in the inventory stops the run.
- Rule parameters in `config/classify_rules.yaml`: end-of-life OS names, database name patterns and environment patterns.

## The rules

Rules run in a fixed order and the **first match decides**. The order expresses priority: what the owner says beats what the data suggests, and data problems are caught before any strategy is proposed.

| # | Rule | Condition | Strategy | Confidence | Review |
| --- | --- | --- | --- | --- | --- |
| 1 | `owner-decision` | A tag sets `decision` | As tagged | High | No |
| 2 | `incomplete-data` | Zero disk or zero vCPU | Retain | Low | Yes |
| 3 | `template` | VM template | Retire (rebuild as a target image) | High | No |
| 4 | `not-running` | Powered off or suspended | Retire | Medium | Yes |
| 5 | `unknown-os` | No OS reported | Retain | Low | Yes |
| 6 | `end-of-life-os` | OS on the end-of-life list | Replatform | Medium | No |
| 7 | `database` | Name matches a database pattern | Replatform | Medium | No |
| 8 | `default` | Everything else | Rehost | High | No |

Why this order:

- **Owner first.** Business decisions such as "moving to a SaaS ERP" cannot be inferred from an inventory.
- **Bad data second.** A VM with no disk is more likely a stale record than a workload; planning around it would be wrong.
- **Retain when unsure.** Retaining is the safe default when data is missing: nothing is moved or deleted until someone confirms.
- **Not-running before end-of-life.** A powered-off VM on an old OS should be questioned before anyone spends effort upgrading it.

## Environment

The environment drives wave planning later (non-production first). It comes from the tag if present, otherwise from the folder, otherwise from the VM name, and the output records which source was used. If nothing matches, it is `unknown` rather than guessed.

## Output

`classified.json`: one record per VM with `strategy`, `rule`, `reasons`, `confidence`, `needs_review`, environment, application, owner and criticality, plus a summary of counts per strategy.

## Run it

```bash
exitplaybook-classify --inventory runs/inventory.json --tags samples/app_tags.csv --output runs/classified.json
```

## Tuning

- **Your lifecycle policy differs:** edit `end_of_life_os` in `config/classify_rules.yaml`.
- **Your naming convention differs:** edit `database_name_patterns` and `environment_patterns`.
- **A strategy is a business call:** set it in the tags file; the owner's decision always wins.
