# Kafka Consumer Lag Alerting Runbook

Version 2 · Effective 2026-03-01 · Owner: Streaming SRE

## When to use this runbook

Use this runbook when a consumer group on the production cluster falls behind
its topics. It defines the alert thresholds, where the alert comes from, and the
first actions on-call takes.

## Alert thresholds

- **Warning:** consumer lag above 5 minutes of time lag for 5 minutes. Posts to the team channel only.
- **Page:** consumer lag above 10 minutes of time lag for 5 minutes. Pages the primary on-call.
- Consumer groups whose name starts with `test-` or `tmp-` never alert.

## Where the numbers come from

Lag is collected by **kafka-lag-exporter**, which exposes metrics on port **9308**.
The alert rule reads the metric `kafka_consumergroup_lag_seconds`. The dashboard is **Kafka Consumer Health**
in Grafana.

## First response

1. Open the dashboard and confirm which partitions are behind.
2. Check that the consumer pods are running: `kubectl get pods -l app=<group>`.
3. Scale the consumer deployment out, up to twice its normal replica count.
4. If lag is still growing after 20 minutes, follow the on-call escalation runbook.
