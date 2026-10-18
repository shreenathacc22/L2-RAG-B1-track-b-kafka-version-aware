"""Generate the Track B Kafka corpus: 8 subjects x (current, old), plus manifest.json.

    python make_corpus.py <track-b-kafka>/simple_rag/corpus/kafka

Each pair shares one template, so wording is identical and only the facts differ.
The manifest is written from the same data, so metadata and text cannot drift.
Output is deterministic: re-running reproduces the committed files byte for byte.
"""
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

PAIRS = [
# ── 1 ─────────────────────────────────────────────────────────────────────────
dict(cur="consumer-lag-alerting.md", old="consumer-lag-alerting-2024.md",
title="Kafka Consumer Lag Alerting Runbook",
tpl="""# {title}

Version {version} · Effective {date} · Owner: {owner}

## When to use this runbook

Use this runbook when a consumer group on the production cluster falls behind
its topics. It defines the alert thresholds, where the alert comes from, and the
first actions on-call takes.

## Alert thresholds

- **Warning:** {warn}. Posts to the team channel only.
- **Page:** {page}. Pages the primary on-call.
- Consumer groups whose name starts with `test-` or `tmp-` never alert.

## Where the numbers come from

Lag is collected by **{exporter}**, which exposes metrics on port **{exp_port}**.
The alert rule reads the metric `{metric}`. The dashboard is **{dashboard}**
in Grafana.

## First response

1. Open the dashboard and confirm which partitions are behind.
2. Check that the consumer pods are running: `kubectl get pods -l app=<group>`.
3. {action}
4. If lag is still growing after 20 minutes, follow the on-call escalation runbook.
""",
c=dict(version=2, date="2026-03-01", owner="Streaming SRE",
       warn="consumer lag above 5 minutes of time lag for 5 minutes",
       page="consumer lag above 10 minutes of time lag for 5 minutes",
       exporter="kafka-lag-exporter", exp_port=9308,
       metric="kafka_consumergroup_lag_seconds", dashboard="Kafka Consumer Health",
       action="Scale the consumer deployment out, up to twice its normal replica count."),
o=dict(version=1, date="2024-06-01", owner="Data Platform",
       warn="consumer lag above 50,000 messages for 5 minutes",
       page="consumer lag above 100,000 messages for 5 minutes",
       exporter="lag-monitor", exp_port=9999,
       metric="kafka_consumergroup_lag", dashboard="Kafka Lag (legacy)",
       action="Restart the consumer deployment with `kubectl rollout restart`."),
conflicts=["page threshold", "warning threshold", "exporter", "exporter port", "metric", "dashboard", "owner", "first action"]),

# ── 2 ─────────────────────────────────────────────────────────────────────────
dict(cur="topic-retention.md", old="topic-retention-2024.md",
title="Kafka Topic Retention Policy",
tpl="""# {title}

Version {version} · Effective {date} · Owner: {owner}

## Purpose

This policy sets how long data stays on production Kafka topics and who may
change it. Retention is the main lever on broker disk usage.

## Defaults for new topics

- `retention.ms` default: **{ret_ms}** ({ret_human}).
- `retention.bytes` default: **{ret_bytes}**.
- `cleanup.policy` default: `delete`. Compacted topics must say so explicitly.
- Compacted topics use `min.compaction.lag.ms` of **{compact}**.

## Changing retention

- Teams may set retention themselves up to **{self_max}**.
- Anything longer needs approval from **{approver}**.
- Make the change with: `{tool}`.
- Audit topics (prefix `audit.`) are kept for **{audit}** and cannot be shortened.

## Verify

Describe the topic config after the change and confirm the value appears.
""",
c=dict(version=3, date="2026-01-15", owner="Streaming SRE",
       ret_ms=259200000, ret_human="3 days", ret_bytes="53687091200 (50 GiB per partition)",
       compact="6 hours", self_max="7 days", approver="the Architecture Review Board",
       tool="kctl topic set-retention <topic> --ms <value>", audit="180 days"),
o=dict(version=2, date="2024-09-01", owner="Data Platform",
       ret_ms=604800000, ret_human="7 days", ret_bytes="-1 (unlimited)",
       compact="1 hour", self_max="14 days", approver="Data Governance",
       tool="kafka-configs.sh --alter --entity-type topics --entity-name <topic> --add-config retention.ms=<value>",
       audit="90 days"),
conflicts=["default retention", "retention.bytes", "compaction lag", "self-service max", "approver", "tool", "audit retention"]),

# ── 3 ─────────────────────────────────────────────────────────────────────────
dict(cur="broker-rolling-restart.md", old="broker-rolling-restart-2025.md",
title="Kafka Broker Rolling Restart Procedure",
tpl="""# {title}

Version {version} · Effective {date} · Owner: {owner}

## When to use this procedure

Use this procedure to restart every broker in the production cluster one at a
time, for config changes, OS patching or a Kafka upgrade. Never restart more
than one broker at a time.

## Before you start

- Change record: {change}.
- Window: **{window}**.
- Pre-check: {precheck}.

## Steps

1. Restart brokers in this order: {order}.
2. Restart the broker with: `{command}`.
3. Allow controlled shutdown up to **{shutdown}** before forcing it.
4. Wait **{wait}** after the broker rejoins, then re-run the pre-check.
5. Move to the next broker only when the pre-check passes again.

## Abort

If a pre-check fails twice in a row, stop and page the on-call.
""",
c=dict(version=4, date="2026-04-01", owner="Streaming SRE",
       change="use the pre-approved standard change template `STD-KAFKA-ROLL`",
       window="Wednesday 14:00–17:00 UTC",
       precheck="under-replicated partitions = 0 and under-min-ISR partitions = 0",
       order="all non-controller brokers by ascending id, the active controller last",
       command="kctl broker restart --id <n>", shutdown="180 seconds", wait="10 minutes"),
o=dict(version=3, date="2025-03-10", owner="Data Platform",
       change="raise a normal change and get CAB approval",
       window="Tuesday or Thursday 22:00–02:00 UTC",
       precheck="under-replicated partitions = 0",
       order="by ascending broker id",
       command="sudo systemctl restart kafka", shutdown="60 seconds", wait="5 minutes"),
conflicts=["change record", "window", "pre-check", "order", "command", "shutdown timeout", "wait between brokers"]),

# ── 4 ─────────────────────────────────────────────────────────────────────────
dict(cur="listeners-and-auth.md", old="listeners-and-auth-2024.md",
title="Kafka Listeners and Client Authentication",
tpl="""# {title}

Version {version} · Effective {date} · Owner: {owner}

## Purpose

How applications connect to the production Kafka cluster and how they
authenticate.

## Client connection

- Bootstrap servers: `{bootstrap}`.
- Client listener: port **{port}**, protocol **{protocol}**.
- SASL mechanism: **{mech}**.
- Minimum TLS version: **{tls}**.

## Inter-broker traffic

Brokers talk to each other on port **{ib_port}** using **{ib_proto}**.

## Credentials

- Client credentials are issued {creds}.
- Client certificates are rotated every **{rotate}**.

## Troubleshooting

`Connection to node -1 could not be established` almost always means the client
is pointed at the wrong port or protocol. Compare the client config with the
values above.
""",
c=dict(version=3, date="2026-02-01", owner="Streaming SRE",
       bootstrap="kafka.prod.halcyon.internal:9094", port=9094, protocol="SASL_SSL",
       mech="SCRAM-SHA-512", tls="1.3", ib_port=9093, ib_proto="SSL",
       creds="per application from Vault at `secret/kafka/clients/<app>`", rotate="90 days"),
o=dict(version=1, date="2024-03-01", owner="Data Platform",
       bootstrap="kafka-prod.halcyon.internal:9092", port=9092, protocol="PLAINTEXT",
       mech="none (PLAINTEXT has no authentication)", tls="1.2", ib_port=9091, ib_proto="PLAINTEXT",
       creds="as the shared `svc-kafka` account; the password is on the team wiki", rotate="365 days"),
conflicts=["bootstrap", "client port", "protocol", "SASL mechanism", "TLS version", "inter-broker port", "inter-broker protocol", "credentials", "rotation"]),

# ── 5 ─────────────────────────────────────────────────────────────────────────
dict(cur="topic-creation-standards.md", old="topic-creation-standards-2024.md",
title="Kafka Topic Creation Standards",
tpl="""# {title}

Version {version} · Effective {date} · Owner: {owner}

## Purpose

Every new production topic must follow these standards so that capacity,
ownership and naming stay predictable.

## Naming

Topic names follow `{naming}`, lowercase, dots as separators.
Example: `{example}`.

## Required settings

- Partitions: **{parts}** by default.
- Replication factor: **3**.
- `min.insync.replicas`: **{min_isr}**.
- Topics over **{max_parts}** partitions need a capacity review.

## How to request a topic

{request}

## Not allowed

Auto-created topics are disabled on production (`auto.create.topics.enable=false`).
""",
c=dict(version=3, date="2026-02-15", owner="Streaming SRE",
       naming="<domain>.<team>.<dataset>.v<N>", example="payments.ledger.transactions.v1",
       parts=12, min_isr=2, max_parts=96,
       request="Open a pull request in the `kafka-topics` Terraform repository. CI validates the name and settings."),
o=dict(version=2, date="2024-05-20", owner="Data Platform",
       naming="<team>.<dataset>", example="ledger.transactions",
       parts=6, min_isr=1, max_parts=50,
       request="Open a Jira ticket in the KAFKA project. The Data Platform team creates the topic by hand."),
conflicts=["naming", "partitions", "min.insync.replicas", "review threshold", "request process"]),

# ── 6 ─────────────────────────────────────────────────────────────────────────
dict(cur="disk-capacity.md", old="disk-capacity-2025.md",
title="Kafka Broker Disk Capacity Runbook",
tpl="""# {title}

Version {version} · Effective {date} · Owner: {owner}

## Scope

Disk usage on the Kafka data volume `/var/lib/kafka` on every production
broker.

## Alert thresholds

- **Warning** at **{warn}** used.
- **Page** at **{page}** used.
- **Emergency** at **{emerg}** used: stop all non-critical producers.

## First response

1. Find the largest topics: `du -sh /var/lib/kafka/* | sort -h | tail`.
2. {action}
3. If usage is still rising, expand the volume by **{expand}**.

## Capacity review

Disk headroom is reviewed **{review}** with the infrastructure team.
""",
c=dict(version=3, date="2026-05-01", owner="Streaming SRE",
       warn="75%", page="85%", emerg="92%",
       action="Lower retention on the three largest topics with `kctl topic set-retention`. Never delete segment files by hand.",
       expand="1 TiB", review="monthly"),
o=dict(version=2, date="2025-02-01", owner="Data Platform",
       warn="80%", page="90%", emerg="95%",
       action="Delete the oldest log segment files of the largest topic by hand.",
       expand="500 GiB", review="quarterly"),
conflicts=["warning", "page", "emergency", "first action", "expansion size", "review cadence"]),

# ── 7 ─────────────────────────────────────────────────────────────────────────
dict(cur="schema-registry.md", old="schema-registry-2024.md",
title="Kafka Schema Registry Operations",
tpl="""# {title}

Version {version} · Effective {date} · Owner: {owner}

## Endpoint

- URL: `{url}`.
- Port: **{port}**.
- Authentication: **{auth}**.

## Compatibility

The default compatibility level is **{compat}**. Subjects use
`TopicNameStrategy`, so the subject for topic `orders.v1` is `orders.v1-value`.

## Registering schemas

{register}

## Deleting schemas

{delete}
""",
c=dict(version=2, date="2026-03-20", owner="Streaming SRE",
       url="https://schemas.prod.halcyon.internal:8085", port=8085, auth="mutual TLS",
       compat="FULL_TRANSITIVE",
       register="Only the CI pipeline may register schemas. Services read schemas but never write them.",
       delete="Deleting a schema version is forbidden. Raise it with the Architecture Review Board."),
o=dict(version=1, date="2024-07-15", owner="Data Platform",
       url="http://schema-registry.halcyon.internal:8081", port=8081, auth="none",
       compat="BACKWARD",
       register="Any service may register a schema on first produce.",
       delete="Soft-delete a schema version with `DELETE /subjects/<subject>/versions/<n>`."),
conflicts=["url", "port", "auth", "compatibility", "who registers", "delete policy"]),

# ── 8 ─────────────────────────────────────────────────────────────────────────
dict(cur="oncall-escalation.md", old="oncall-escalation-2025.md",
title="Kafka On-Call Escalation Policy",
tpl="""# {title}

Version {version} · Effective {date} · Owner: {owner}

## Who is on call

The **{team}** team owns production Kafka incidents. Pages arrive through the
PagerDuty service **`{pd}`**.

## Response times

- Primary acknowledges within **{ack}**.
- No acknowledgement: escalate to the secondary after **{secondary}**.
- Not resolved: escalate to the engineering manager after **{manager}**.

## SEV-1

Declare it with {declare}, and post updates in **{channel}** every 15 minutes.

## After the incident

Write the post-incident review within five working days.
""",
c=dict(version=3, date="2026-06-01", owner="Streaming SRE",
       team="Streaming SRE", pd="streaming-platform-prod", ack="5 minutes",
       secondary="15 minutes", manager="30 minutes",
       declare="`/incident declare` in Slack, which opens the bridge", channel="#inc-streaming"),
o=dict(version=2, date="2025-01-10", owner="Data Platform",
       team="Data Platform", pd="kafka-ops", ack="15 minutes",
       secondary="30 minutes", manager="60 minutes",
       declare="a Zoom bridge started by the primary", channel="#kafka-alerts"),
conflicts=["team", "PagerDuty service", "ack", "secondary", "manager", "declare", "channel"]),
]

HEADER_KEYS = {"version", "date"}   # carried as metadata, not listed as conflicts

files, conflicts = {}, {}
for p in PAIRS:
    for key, fname in (("c", p["cur"]), ("o", p["old"])):
        text = p["tpl"].format(title=p["title"], **p[key])
        (OUT / fname).write_text(text, encoding="utf-8")
        files[fname] = {"doc": p["title"], "version": p[key]["version"],
                        "effective_date": p[key]["date"], "superseded": key == "o"}
    conflicts[p["title"]] = [
        {"field": k, "old": str(p["o"][k]), "current": str(p["c"][k])}
        for k in p["c"] if k not in HEADER_KEYS and p["c"][k] != p["o"][k]]

manifest = {
    "_about": ("B1 Track B metadata. 'files' is what ingest attaches to every chunk "
               "(doc, version, effective_date, superseded). 'conflicts' lists every "
               "value that differs between versions; it is source material for golden "
               "cases and is never given to the retriever."),
    "files": dict(sorted(files.items())),
    "conflicts": conflicts,
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
print(f"wrote {len(files)} runbooks + manifest.json to {OUT}")
