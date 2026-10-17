# Kafka Broker Rolling Restart Procedure

Version 4 · Effective 2026-04-01 · Owner: Streaming SRE

## When to use this procedure

Use this procedure to restart every broker in the production cluster one at a
time, for config changes, OS patching or a Kafka upgrade. Never restart more
than one broker at a time.

## Before you start

- Change record: use the pre-approved standard change template `STD-KAFKA-ROLL`.
- Window: **Wednesday 14:00–17:00 UTC**.
- Pre-check: under-replicated partitions = 0 and under-min-ISR partitions = 0.

## Steps

1. Restart brokers in this order: all non-controller brokers by ascending id, the active controller last.
2. Restart the broker with: `kctl broker restart --id <n>`.
3. Allow controlled shutdown up to **180 seconds** before forcing it.
4. Wait **10 minutes** after the broker rejoins, then re-run the pre-check.
5. Move to the next broker only when the pre-check passes again.

## Abort

If a pre-check fails twice in a row, stop and page the on-call.
