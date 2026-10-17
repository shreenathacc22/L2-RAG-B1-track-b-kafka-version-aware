# Kafka Broker Disk Capacity Runbook

Version 3 · Effective 2026-05-01 · Owner: Streaming SRE

## Scope

Disk usage on the Kafka data volume `/var/lib/kafka` on every production
broker.

## Alert thresholds

- **Warning** at **75%** used.
- **Page** at **85%** used.
- **Emergency** at **92%** used: stop all non-critical producers.

## First response

1. Find the largest topics: `du -sh /var/lib/kafka/* | sort -h | tail`.
2. Lower retention on the three largest topics with `kctl topic set-retention`. Never delete segment files by hand.
3. If usage is still rising, expand the volume by **1 TiB**.

## Capacity review

Disk headroom is reviewed **monthly** with the infrastructure team.
