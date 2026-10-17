# Kafka Broker Disk Capacity Runbook

Version 2 · Effective 2025-02-01 · Owner: Data Platform

## Scope

Disk usage on the Kafka data volume `/var/lib/kafka` on every production
broker.

## Alert thresholds

- **Warning** at **80%** used.
- **Page** at **90%** used.
- **Emergency** at **95%** used: stop all non-critical producers.

## First response

1. Find the largest topics: `du -sh /var/lib/kafka/* | sort -h | tail`.
2. Delete the oldest log segment files of the largest topic by hand.
3. If usage is still rising, expand the volume by **500 GiB**.

## Capacity review

Disk headroom is reviewed **quarterly** with the infrastructure team.
