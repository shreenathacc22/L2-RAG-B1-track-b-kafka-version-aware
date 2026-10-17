# Kafka Listeners and Client Authentication

Version 3 · Effective 2026-02-01 · Owner: Streaming SRE

## Purpose

How applications connect to the production Kafka cluster and how they
authenticate.

## Client connection

- Bootstrap servers: `kafka.prod.halcyon.internal:9094`.
- Client listener: port **9094**, protocol **SASL_SSL**.
- SASL mechanism: **SCRAM-SHA-512**.
- Minimum TLS version: **1.3**.

## Inter-broker traffic

Brokers talk to each other on port **9093** using **SSL**.

## Credentials

- Client credentials are issued per application from Vault at `secret/kafka/clients/<app>`.
- Client certificates are rotated every **90 days**.

## Troubleshooting

`Connection to node -1 could not be established` almost always means the client
is pointed at the wrong port or protocol. Compare the client config with the
values above.
