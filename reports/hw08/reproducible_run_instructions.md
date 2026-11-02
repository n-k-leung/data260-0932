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
1. do the following instructions (one terminal):