# Kafka On-Call Escalation Policy

Version 2 · Effective 2025-01-10 · Owner: Data Platform

## Who is on call

The **Data Platform** team owns production Kafka incidents. Pages arrive through the
PagerDuty service **`kafka-ops`**.

## Response times

- Primary acknowledges within **15 minutes**.
- No acknowledgement: escalate to the secondary after **30 minutes**.
- Not resolved: escalate to the engineering manager after **60 minutes**.

## SEV-1

Declare it with a Zoom bridge started by the primary, and post updates in **#kafka-alerts** every 15 minutes.

## After the incident

Write the post-incident review within five working days.
