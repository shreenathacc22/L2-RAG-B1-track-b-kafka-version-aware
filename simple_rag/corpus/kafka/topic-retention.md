# Kafka Topic Retention Policy

Version 3 · Effective 2026-01-15 · Owner: Streaming SRE

## Purpose

This policy sets how long data stays on production Kafka topics and who may
change it. Retention is the main lever on broker disk usage.

## Defaults for new topics

- `retention.ms` default: **259200000** (3 days).
- `retention.bytes` default: **53687091200 (50 GiB per partition)**.
- `cleanup.policy` default: `delete`. Compacted topics must say so explicitly.
- Compacted topics use `min.compaction.lag.ms` of **6 hours**.

## Changing retention

- Teams may set retention themselves up to **7 days**.
- Anything longer needs approval from **the Architecture Review Board**.
- Make the change with: `kctl topic set-retention <topic> --ms <value>`.
- Audit topics (prefix `audit.`) are kept for **180 days** and cannot be shortened.

## Verify

Describe the topic config after the change and confirm the value appears.
