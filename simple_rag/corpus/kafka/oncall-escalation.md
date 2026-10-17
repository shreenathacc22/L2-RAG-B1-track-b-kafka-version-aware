# Kafka On-Call Escalation Policy

Version 3 · Effective 2026-06-01 · Owner: Streaming SRE

## Who is on call

The **Streaming SRE** team owns production Kafka incidents. Pages arrive through the
PagerDuty service **`streaming-platform-prod`**.

## Response times

- Primary acknowledges within **5 minutes**.
- No acknowledgement: escalate to the secondary after **15 minutes**.
- Not resolved: escalate to the engineering manager after **30 minutes**.

## SEV-1

Declare it with `/incident declare` in Slack, which opens the bridge, and post updates in **#inc-streaming** every 15 minutes.

## After the incident

Write the post-incident review within five working days.
