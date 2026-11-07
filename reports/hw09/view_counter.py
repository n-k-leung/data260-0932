import redis
from sqlalchemy import inspect, text
from app.database import SessionLocal, engine
from app.models import Vul

PREFIX = "s0932"
class VulnerabilityDatabaseWithCache:
    def __init__(self, redis_host="localhost", redis_port=6379):
        self.db = SessionLocal()
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        try:
            self.redis_client.ping()
            print("connected to redis")
        except redis.ConnectionError:
            print("failed to connect to Redis")
            raise

        self._setup_database()

    def _setup_database(self):
        columns = [column["name"] for column in inspect(engine).get_columns("vulnerabilities")]
        if "view_count" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE vulnerabilities ADD COLUMN view_count INT NOT NULL DEFAULT 0"))
            print("Added view_count column to the vulnerabilities table")

    def increment_vulnerability_views(self, vul_id):
        key = f"{PREFIX}:views:vulnerability:{vul_id}"
        count = self.redis_client.incr(key)
        #every 10 increments is saved to the database row
        if count % 10 == 0:
            vul = self.db.query(Vul).filter(Vul.id == vul_id).first()
            vul.view_count = count
            self.db.commit()
            print("✓ Synced views to database")
        return count

    def close(self):
        self.db.close()
        self.redis_client.close()

def run_test():
    db = VulnerabilityDatabaseWithCache()
    #using first vul in the table for test
    vul = db.db.query(Vul).order_by(Vul.id.asc()).first()
    if vul is None:
        print("No vulnerabilities in the database to use")
        db.close()
        return
    vul_id = vul.id
    print(f"Testing vulnerability id={vul_id} (package: {vul.package_name})")

    #need to start counter from 0 so starts at 1
    db.redis_client.delete(f"{PREFIX}:views:vulnerability:{vul_id}")
    print("\n=== Testing Counter ===\n")
    for i in range(1, 26):
        total = db.increment_vulnerability_views(vul_id)
        print(f"Access #{i}: Total = {total}")
    db.db.refresh(vul)
    print(f"\ndatabase view_count for id={vul_id}: {vul.view_count}")
    print(f"redis value for {PREFIX}:views:vulnerability:{vul_id}: {db.redis_client.get(f'{PREFIX}:views:vulnerability:{vul_id}')}")

    db.close()

if __name__ == "__main__":
    run_test()
