# Kafka Consumer Lag Alerting Runbook

Version 1 · Effective 2024-06-01 · Owner: Data Platform

## When to use this runbook

Use this runbook when a consumer group on the production cluster falls behind
its topics. It defines the alert thresholds, where the alert comes from, and the
first actions on-call takes.

## Alert thresholds

- **Warning:** consumer lag above 50,000 messages for 5 minutes. Posts to the team channel only.
- **Page:** consumer lag above 100,000 messages for 5 minutes. Pages the primary on-call.
- Consumer groups whose name starts with `test-` or `tmp-` never alert.

## Where the numbers come from

Lag is collected by **lag-monitor**, which exposes metrics on port **9999**.
The alert rule reads the metric `kafka_consumergroup_lag`. The dashboard is **Kafka Lag (legacy)**
in Grafana.

## First response

1. Open the dashboard and confirm which partitions are behind.
2. Check that the consumer pods are running: `kubectl get pods -l app=<group>`.
3. Restart the consumer deployment with `kubectl rollout restart`.
4. If lag is still growing after 20 minutes, follow the on-call escalation runbook.
