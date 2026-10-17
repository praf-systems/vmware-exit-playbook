# ADR 0002: Rules infer only four of the 7Rs

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

Stage 2 assigns a 7R strategy to every VM. An inventory export describes technical facts: power state, OS, size, folder and name. Some strategies follow from those facts. Others depend on business plans, contracts or architecture choices that no export contains.

## Decision

Automatic rules infer only **retire, retain, rehost and replatform**. **Relocate, repurchase and refactor** are set by the application owner through the tags file. An owner's decision always overrides the rules, and every result records which rule decided it and why.

When data is missing or contradictory, the rules choose **retain** and flag the VM for review rather than guessing.

## Consequences

- **Positive:** every automatic recommendation can be explained from the data; nothing is moved or retired on a guess; owners stay in control of business decisions.
- **Negative:** a large estate without tags will be mostly rehost, and will undercount refactor and repurchase opportunities.
- **Mitigation:** the summary reports how many VMs need review, and the tags file is a simple CSV that application owners can fill in during discovery workshops.
