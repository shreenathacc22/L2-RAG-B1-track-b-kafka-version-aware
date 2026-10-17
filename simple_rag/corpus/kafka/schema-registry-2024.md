# Kafka Schema Registry Operations

Version 1 · Effective 2024-07-15 · Owner: Data Platform

## Endpoint

- URL: `http://schema-registry.halcyon.internal:8081`.
- Port: **8081**.
- Authentication: **none**.

## Compatibility

The default compatibility level is **BACKWARD**. Subjects use
`TopicNameStrategy`, so the subject for topic `orders.v1` is `orders.v1-value`.

## Registering schemas

Any service may register a schema on first produce.

## Deleting schemas

Soft-delete a schema version with `DELETE /subjects/<subject>/versions/<n>`.
