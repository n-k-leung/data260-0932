import logging
import os
import sys
from mcp.server.fastmcp import FastMCP

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.database import SessionLocal
from app import models

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("domain_server")

mcp = FastMCP("domain")
def envelope(ok, data=None, error=None):
    return {"ok": ok, "data": data, "error": error}
def get_session():
    return SessionLocal()
@mcp.tool()
def search_vulnerabilities(package_name: str) -> dict:
    if not package_name or not package_name.strip():
        return envelope(False, error="package_name must not be empty")

    db = get_session()
    try:
        rows = db.query(models.Vul).filter(models.Vul.package_name.ilike("%" + package_name + "%")).all()
        results = [{"id": r.id, "package_name": r.package_name, "severity": r.severity,"vul_code": r.vul_code, "vendor_id": r.vendor_id,} for r in rows]
        return envelope(True, data=results)
    except Exception as e:
        logger.error("search_vulnerabilities failed: %s", e)
        return envelope(False, error="database error")
    finally:
        db.close()
        
@mcp.tool()
def get_vulnerability(vuln_id: int) -> dict:
    db = get_session()
    try:
        row = db.query(models.Vul).filter(models.Vul.id == vuln_id).first()
        if not row:
            return envelope(False, error="vulnerability not found")
        data = {"id": row.id, "package_name": row.package_name, "severity": row.severity,"vul_code": row.vul_code, "vendor_id": row.vendor_id, "report_count": row.report_count}
        return envelope(True, data=data)
    except Exception as e:
        logger.error("get_vulnerability failed: %s", e)
        return envelope(False, error="database error")
    finally:
        db.close()
@mcp.tool()
def count_by_severity(min_count: int=0) -> dict:
    db = get_session()
    try:
        rows = db.query(models.Vul.severity, models.Vul.id).all()
        counts = {}
        if min_count<0:
            return envelope(False, error="min_count has to be >= 0")
        for severity, _id in rows:
            counts[severity] = counts.get(severity, 0) + 1
        counts ={k:v for k, v in counts.items() if v>=min_count}
        return envelope(True, data=counts)
    except Exception as e:
        logger.error("count_by_severity failed: %s", e)
        return envelope(False, error="database error")
    finally:
        db.close()

if __name__ == "__main__":
    mcp.run(transport="stdio")