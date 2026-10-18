"""Generate the frozen B1 Track B golden set: 21 cases -> golden_kafka.jsonl.

    python make_golden.py <track-b-kafka>/simple_rag/golden_kafka.jsonl

Output is deterministic. The frozen file (commit db846c1) has
sha1 850c67f2eab21aa1a6afabd481e5c3efccb7e0ba; re-running must reproduce it exactly.
"""
import json
import sys

OUT = sys.argv[1]

D = {  # doc titles, as in corpus/kafka/manifest.json
    "lag": "Kafka Consumer Lag Alerting Runbook", "ret": "Kafka Topic Retention Policy",
    "roll": "Kafka Broker Rolling Restart Procedure", "lis": "Kafka Listeners and Client Authentication",
    "top": "Kafka Topic Creation Standards", "disk": "Kafka Broker Disk Capacity Runbook",
    "sch": "Kafka Schema Registry Operations", "onc": "Kafka On-Call Escalation Policy"}
V = {"lag": (2, 1), "ret": (3, 2), "roll": (4, 3), "lis": (3, 1), "top": (3, 2), "disk": (3, 2),
     "sch": (2, 1), "onc": (3, 2)}  # (current version, old version)
cur = lambda k: {"doc": D[k], "version": V[k][0]}
old = lambda k: {"doc": D[k], "version": V[k][1]}


def case(n, typ, bucket, q, facts, cite=(), not_cite=(), not_contain=(), forbidden=(), rubric="",
         why="", behavior="answer"):
    return {"id": f"kafka-{n:03d}", "type": typ, "class": "accuracy", "bucket": bucket, "question": q,
            "expect": {"behavior": behavior, "facts": list(facts), "must_cite": [cur(k) for k in cite],
                       "must_not_cite": [old(k) for k in not_cite],
                       "must_not_contain": list(not_contain), "forbidden": list(forbidden)},
            "rubric": rubric, "why": why}


C = [
# ── superseded: old and current give opposite answers ──
case(1, "superseded", "version_conflict",
 "Broker 4's data volume just hit 87%. Should that have paged someone?",
 ["Yes. The page threshold is 85% used, so 87% pages the on-call"], ["disk"], ["disk"], ["90%"],
 ["Saying 87% is below the page threshold"],
 "Pass: yes, it pages, because the threshold is 85%. Fail: 'no, it pages at 90%' (the v2 rule).",
 "87% sits between the old (90%) and current (85%) page lines, so the two versions give opposite answers."),
case(2, "superseded", "version_conflict",
 "Our payments consumers are about 8 minutes behind, roughly 30,000 messages. Does that page anyone?",
 ["No page; it is a warning. Warning is above 5 minutes of time lag, the page is above 10 minutes"],
 ["lag"], ["lag"], ["100,000 messages", "50,000 messages"], ["Judging the lag by message count"],
 "Pass: warning only, page at 10 minutes of time lag. Fail: any answer based on message-count thresholds.",
 "Old runbook measures lag in messages, current in time. 8 minutes is between the 5-minute warning and the 10-minute page."),
case(3, "superseded", "version_conflict",
 "I created a topic and never set retention. How long will messages stay around?",
 ["3 days (retention.ms 259200000)"], ["ret"], ["ret"], ["604800000"], ["Quoting 7 days as the default"],
 "Pass: 3 days. Fail: 7 days / 604800000 (the v2 default). Note 7 days is the current self-service maximum, not the default.",
 "The current file mentions '7 days' as a limit, so a stale answer can look plausible to a reader."),
case(4, "superseded", "version_conflict",
 "Broker 2 just rejoined after its restart. How long until I can bounce broker 3?",
 ["10 minutes after the broker rejoins, and only once the pre-check passes again"], ["roll"], ["roll"], ["5 minutes"],
 ["Saying 5 minutes"], "Pass: 10 minutes. Fail: 5 minutes.",
 "Wait time is the single most-used number in the procedure; a stale value shortens recovery margins."),
case(5, "superseded", "version_conflict",
 "What host and port do I put in my new producer's bootstrap config?",
 ["kafka.prod.halcyon.internal:9094, SASL_SSL"], ["lis"], ["lis"], ["9092", "kafka-prod.halcyon.internal"],
 ["Giving the PLAINTEXT listener"], "Pass: 9094 with SASL_SSL. Fail: 9092 or the kafka-prod host.",
 "Wrong port is a connection failure at best and an unauthenticated client at worst."),
case(6, "superseded", "version_conflict",
 "I'm spinning up a topic with the standard settings. How many partitions and what min ISR?",
 ["12 partitions", "min.insync.replicas 2"], ["top"], ["top"], [],
 ["Saying 6 partitions or min ISR 1"], "Pass: 12 and 2. Fail: 6 and/or 1.",
 "Two conflicting values in one answer; a half-stale answer must fail."),
case(7, "superseded", "version_conflict",
 "What URL should my serializer use to reach the schema registry?",
 ["https://schemas.prod.halcyon.internal:8085"], ["sch"], ["sch"], ["8081"], ["Giving the plain-HTTP 8081 endpoint"],
 "Pass: the https 8085 URL. Fail: anything on 8081.",
 "Endpoint changed host, scheme and port; any stale piece breaks the client."),
case(8, "superseded", "version_conflict",
 "I'm primary on-call and Kafka just paged me. How long do I have to acknowledge?",
 ["5 minutes"], ["onc"], ["onc"], [], ["Saying 15 minutes"],
 "Pass: 5 minutes. Fail: 15 minutes (v2). Note 15 minutes is the current secondary-escalation time, not the ack time.",
 "The stale value (15) also appears in the current doc with a different meaning — a trap for the answer, not only retrieval."),
case(9, "superseded", "version_conflict",
 "Which PagerDuty service do I trigger for a production Kafka problem?",
 ["streaming-platform-prod"], ["onc"], ["onc"], ["kafka-ops"], ["Naming kafka-ops"],
 "Pass: streaming-platform-prod. Fail: kafka-ops.",
 "Paging a retired service during an incident means nobody answers."),
# ── exact_string: literal values; the filter must not hurt these ──
case(10, "exact_string", "exact_value",
 "Can producers auto-create topics on prod? What's the broker setting?",
 ["auto.create.topics.enable=false"], ["top"],
 rubric="Pass: names the exact setting with false.", why="Same in both versions: the filter changes nothing here, so the score must stay flat."),
case(11, "exact_string", "exact_value",
 "Which mount should I watch for Kafka broker disk alerts?",
 ["/var/lib/kafka"], ["disk"], rubric="Pass: /var/lib/kafka.", why="Version-neutral path."),
case(12, "exact_string", "exact_value",
 "What command tells me whether a lagging group's consumer pods are actually running?",
 ["kubectl get pods -l app=<group>"], ["lag"], rubric="Pass: the exact kubectl command.", why="Version-neutral command."),
case(13, "exact_string", "exact_value",
 "What's the registry subject for the value schema of topic orders.v1?",
 ["orders.v1-value"], ["sch"], rubric="Pass: orders.v1-value.", why="Version-neutral identifier derived from TopicNameStrategy."),
case(14, "exact_string", "exact_value",
 "My app can't connect and logs a node -1 error. What's the exact message, and what does it usually mean?",
 ["Connection to node -1 could not be established"], ["lis"],
 rubric="Pass: quotes the error text.", why="Version-neutral error string; retrieval must still find the listeners doc."),
case(15, "exact_string", "exact_value",
 "What's the change template ID for a broker rolling restart?",
 ["STD-KAFKA-ROLL"], ["roll"], ["roll"], forbidden=["Saying a CAB approval is needed"],
 rubric="Pass: STD-KAFKA-ROLL.", why="Identifier that exists only in the current version."),
case(16, "exact_string", "exact_value",
 "Where in Vault do I find my app's Kafka client credentials?",
 ["secret/kafka/clients/<app>"], ["lis"], ["lis"], ["svc-kafka"], ["Pointing to the shared svc-kafka account"],
 rubric="Pass: the Vault path.", why="Current-only path; the old doc points to a shared password on a wiki."),
# ── multi_hop: one fact from each of two current docs ──
case(17, "multi_hop", "mixed",
 "Disk on broker 3 just crossed the page line. What is that line, and which PagerDuty service gets the page?",
 ["85%", "streaming-platform-prod"], ["disk", "onc"], ["disk", "onc"], ["90%", "kafka-ops"],
 rubric="Both parts required, both current.", why="Needs two documents; stale chunks waste top-k slots the second document needs."),
case(18, "multi_hop", "mixed",
 "New topic, all defaults: how many partitions does it get and how long is data kept?",
 ["12 partitions", "3 days"], ["top", "ret"], ["top", "ret"], ["604800000"],
 rubric="Both parts required, both current.", why="Topic creation and retention are separate runbooks."),
case(19, "multi_hop", "mixed",
 "I'm rolling the brokers for a TLS change. How long do I wait between brokers, and which client port should be healthy afterwards?",
 ["10 minutes", "9094"], ["roll", "lis"], ["roll", "lis"], ["9092"],
 rubric="Both parts required, both current.", why="Procedure plus connection facts from two documents."),
# ── unanswerable: Kafka questions the corpus does not cover ──
case(20, "unanswerable", "unanswerable",
 "What's the largest message size our brokers will accept?",
 ["The runbooks do not state a maximum message size"], behavior="refuse",
 forbidden=["Inventing a value such as 1 MB or message.max.bytes=1048588"],
 rubric="Pass: says the documents don't cover it. Fail: any specific number.",
 why="Checks that removing stale chunks does not push the model into guessing."),
case(21, "unanswerable", "unanswerable",
 "How many brokers are in the production cluster?",
 ["The runbooks do not state the broker count"], behavior="refuse",
 forbidden=["Inferring a count from broker numbers mentioned in examples"],
 rubric="Pass: says it is not documented.", why="Plausible question with no answer in the corpus."),
]

with open(OUT, "w", encoding="utf-8") as f:
    for c in C:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print(f"wrote {len(C)} cases to {OUT}")
