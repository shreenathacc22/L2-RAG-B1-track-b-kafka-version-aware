# Kafka Topic Retention Policy

Version 2 · Effective 2024-09-01 · Owner: Data Platform

## Purpose

This policy sets how long data stays on production Kafka topics and who may
change it. Retention is the main lever on broker disk usage.

## Defaults for new topics

- `retention.ms` default: **604800000** (7 days).
- `retention.bytes` default: **-1 (unlimited)**.
- `cleanup.policy` default: `delete`. Compacted topics must say so explicitly.
- Compacted topics use `min.compaction.lag.ms` of **1 hour**.

## Changing retention

- Teams may set retention themselves up to **14 days**.
- Anything longer needs approval from **Data Governance**.
- Make the change with: `kafka-configs.sh --alter --entity-type topics --entity-name <topic> --add-config retention.ms=<value>`.
- Audit topics (prefix `audit.`) are kept for **90 days** and cannot be shortened.

## Verify

Describe the topic config after the change and confirm the value appears.
