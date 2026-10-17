# Kafka Broker Rolling Restart Procedure

Version 3 · Effective 2025-03-10 · Owner: Data Platform

## When to use this procedure

Use this procedure to restart every broker in the production cluster one at a
time, for config changes, OS patching or a Kafka upgrade. Never restart more
than one broker at a time.

## Before you start

- Change record: raise a normal change and get CAB approval.
- Window: **Tuesday or Thursday 22:00–02:00 UTC**.
- Pre-check: under-replicated partitions = 0.

## Steps

1. Restart brokers in this order: by ascending broker id.
2. Restart the broker with: `sudo systemctl restart kafka`.
3. Allow controlled shutdown up to **60 seconds** before forcing it.
4. Wait **5 minutes** after the broker rejoins, then re-run the pre-check.
5. Move to the next broker only when the pre-check passes again.

## Abort

If a pre-check fails twice in a row, stop and page the on-call.
