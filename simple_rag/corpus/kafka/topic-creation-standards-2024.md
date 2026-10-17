# Kafka Topic Creation Standards

Version 2 · Effective 2024-05-20 · Owner: Data Platform

## Purpose

Every new production topic must follow these standards so that capacity,
ownership and naming stay predictable.

## Naming

Topic names follow `<team>.<dataset>`, lowercase, dots as separators.
Example: `ledger.transactions`.

## Required settings

- Partitions: **6** by default.
- Replication factor: **3**.
- `min.insync.replicas`: **1**.
- Topics over **50** partitions need a capacity review.

## How to request a topic

Open a Jira ticket in the KAFKA project. The Data Platform team creates the topic by hand.

## Not allowed

Auto-created topics are disabled on production (`auto.create.topics.enable=false`).
