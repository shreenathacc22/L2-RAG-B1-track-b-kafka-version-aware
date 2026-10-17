# Kafka Topic Creation Standards

Version 3 · Effective 2026-02-15 · Owner: Streaming SRE

## Purpose

Every new production topic must follow these standards so that capacity,
ownership and naming stay predictable.

## Naming

Topic names follow `<domain>.<team>.<dataset>.v<N>`, lowercase, dots as separators.
Example: `payments.ledger.transactions.v1`.

## Required settings

- Partitions: **12** by default.
- Replication factor: **3**.
- `min.insync.replicas`: **2**.
- Topics over **96** partitions need a capacity review.

## How to request a topic

Open a pull request in the `kafka-topics` Terraform repository. CI validates the name and settings.

## Not allowed

Auto-created topics are disabled on production (`auto.create.topics.enable=false`).
