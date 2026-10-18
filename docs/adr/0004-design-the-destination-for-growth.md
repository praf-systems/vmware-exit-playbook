# ADR 0004: Design the destination for growth

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

Some decisions about a destination platform can't be changed once it is deployed, such as the size of a management network range or the size of management appliances. If they are sized only for the first year, growth can force a second migration: a new environment, workloads moved again and firewall rules recreated. I've done that rebuild, and it costs far more than getting the size right would have.

## Decision

Before deploying a destination:

1. List every setting that can't be changed later, each with a link to the documentation that explains it.
2. Read that documentation and confirm how many addresses or resources each host and service really consumes.
3. Size each of those settings for the largest the environment could reasonably grow to, with headroom.
4. Choose the larger size for management components when growth is expected; the extra cost is small.

## Consequences

- **Positive:** growth never forces a rebuild or a second migration.
- **Negative:** slightly higher cost and more address space reserved up front.
- **Mitigation:** firewall rules and groups are kept as code, so if a rebuild is ever needed, they can be reapplied by script instead of by hand.
