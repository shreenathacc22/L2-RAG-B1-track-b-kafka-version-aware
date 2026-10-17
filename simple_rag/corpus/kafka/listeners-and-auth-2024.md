# Kafka Listeners and Client Authentication

Version 1 · Effective 2024-03-01 · Owner: Data Platform

## Purpose

How applications connect to the production Kafka cluster and how they
authenticate.

## Client connection

- Bootstrap servers: `kafka-prod.halcyon.internal:9092`.
- Client listener: port **9092**, protocol **PLAINTEXT**.
- SASL mechanism: **none (PLAINTEXT has no authentication)**.
- Minimum TLS version: **1.2**.

## Inter-broker traffic

Brokers talk to each other on port **9091** using **PLAINTEXT**.

## Credentials

- Client credentials are issued as the shared `svc-kafka` account; the password is on the team wiki.
- Client certificates are rotated every **365 days**.

## Troubleshooting

`Connection to node -1 could not be established` almost always means the client
is pointed at the wrong port or protocol. Compare the client config with the
values above.
