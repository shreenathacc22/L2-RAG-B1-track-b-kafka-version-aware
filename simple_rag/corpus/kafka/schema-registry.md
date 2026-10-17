# Kafka Schema Registry Operations

Version 2 · Effective 2026-03-20 · Owner: Streaming SRE

## Endpoint

- URL: `https://schemas.prod.halcyon.internal:8085`.
- Port: **8085**.
- Authentication: **mutual TLS**.

## Compatibility

The default compatibility level is **FULL_TRANSITIVE**. Subjects use
`TopicNameStrategy`, so the subject for topic `orders.v1` is `orders.v1-value`.

## Registering schemas

Only the CI pipeline may register schemas. Services read schemas but never write them.

## Deleting schemas

Deleting a schema version is forbidden. Raise it with the Architecture Review Board.
