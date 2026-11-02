# part 1
1. do the following instructions (one terminal):
python -c "import secrets; print(secrets.token_hex(32))"
cd .\reports\hw08
docker compose up --build -d
docker ps
docker logs s0932_api
2. do the following instructions (another terminal):
cd .\reports\hw08
python .\homework-demo.py
3. To get the logs do following:
docker logs s0932_worker
docker compose logs -t api worker
docker compose logs -t --since 2026-11-02T09:09:36Z api worker | Sort-Object { ($_ -split '\| ',2)[1] } (for inorder)

# part 2
1. do the following instructions (one per each terminal in this order):
cd .\reports\hw08\agents

python planner.py
python writer.py
python reviewer.py
python send_question.py

2. To check you created the four topics run:
docker exec kafka /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic s0932_inbox --partitions 1 --replication-factor 1 --bootstrap-server localhost:9092
docker exec kafka /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic s0932_tasks --partitions 2 --replication-factor 1 --bootstrap-server localhost:9092
docker exec kafka /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic s0932_drafts --partitions 1 --replication-factor 1 --bootstrap-server localhost:9092
docker exec kafka /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic s0932_final --partitions 1 --replication-factor 1 --bootstrap-server localhost:9092
docker exec kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
docker exec kafka /opt/kafka/bin/kafka-topics.sh --describe --bootstrap-server localhost:9092 --topic s0932_inbox,s0932_tasks,s0932_drafts,s0932_final

# part 3
1. do the following instructions (one time):
cd .\reports\hw08
docker compose up -d
docker exec kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 (check s0932_dead_letter is there)

2. check the writer offsets/LAG at any time run:
docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group s0932-writer-group
all commands below are run in .\reports\hw08\agents (terminal 1 = writer, terminal 2 = test messages). Press Ctrl+C to stop the writer between tests.

3. duplicate delivery:
before fix:
terminal 1: python .\writer.py --before
terminal 2: python .\send_test_task.py duplicate
after fix:
terminal 1: python .\writer.py
terminal 2: python .\send_test_task.py duplicate

4. consumer killed mid-work:
before fix:
terminal 1: python .\writer.py --before --slow
terminal 2: python .\send_test_task.py once
press Ctrl+C in terminal 1 when it says PROCESSING... waiting 15 seconds
terminal 2: run the LAG command from step 2 (LAG = 0)
terminal 1: python .\writer.py --before (message is not redelivered)
after fix:
terminal 1: python .\writer.py --slow
terminal 2: python .\send_test_task.py once
press Ctrl+C in terminal 1 when it says PROCESSING... waiting 15 seconds
terminal 2: run the LAG command from step 2 (LAG = 1)
terminal 1: python .\writer.py (same offset is redelivered, SEND, COMMIT)
terminal 2: run the LAG command from step 2 (LAG = 0)

5. poison message:
before fix:
terminal 1: python .\writer.py --before
terminal 2: python .\send_test_task.py poison (writer crashes with JSONDecodeError)
after fix:
terminal 1: python .\writer.py
terminal 2: python .\send_test_task.py poison
To see the dead letter topic run:
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic s0932_dead_letter --from-beginning --timeout-ms 5000

6. ordering (VERIFY_SEED = 260932), use three terminals:
terminal 1: python .\writer.py A
terminal 2: python .\writer.py B
wait about 10 seconds so the two writers split the 2 partitions
terminal 3: python .\ordering_test.py nokey (run 1, no key)
terminal 3: python .\ordering_test.py key (run 2, key = package name)
results are saved in reports\hw08\raw\ordering_runs_A.csv and ordering_runs_B.csv