import random
from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app import models

def main():
    random. seed (932)


    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    db.query(models.Advisory).delete()
    db.query(models.Vul).delete()
    # make the ids start at 1 again
    db.execute(text("ALTER TABLE vulnerabilities AUTO_INCREMENT = 1"))
    db.execute(text("ALTER TABLE advisories AUTO_INCREMENT = 1"))
    db.commit()

    names = ["lodash", "express", "axios", "requests", "django", "flask", "numpy", "react", "vue", "jquery"]
    severities = ["Low", "Medium", "High", "Critical"]

    vulns = []
    for i in range(5000):
        vulns.append(models.Vul(
            package_name=random. choice(names)+ "-"+str(i),
            severity=random.choice(severities),))

    db.add_all(vulns)
    db.commit()

    ids = [row.id for row in db.query(models.Vul.id).order_by(models.Vul.id).all()]

    advisories = []
    for i in range(200):
        fix = str(random.randint(1, 9)) +"."+ str(random.randint(0, 9)) + "." + str(random.randint(0, 9))
        advisories.append(models.Advisory(vul_id=random.choice(ids[:200]), fix_version=fix))
    db.add_all(advisories)
    db.commit()

    print("Seeded", len(vulns), "vulnerabilities and", len(advisories), "advisories (SEED = 932)")

if __name__ == "__main__":
    main()