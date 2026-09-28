import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchVulById } from "../api/vulApi.js";

export default function UpdateRecord({ onUpdate }) {
  const { id } = useParams();
  const recordId = Number(id);

  const [package_name, setPackageName] = useState("");
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const record = await fetchVulById(recordId);
        setPackageName(record.package_name);
        setSeverity(record.severity);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, [recordId]);

  async function handleSubmit(e) {
    e.preventDefault();
    await onUpdate(recordId, { package_name, severity });
  }

  if (loading) return <p>Loading record...</p>;

  return (
    <div className="card">
        <div className="card-header">
        <div className="page-title">Update Record (ID: {recordId})</div>
        </div>

        <div className="card-body">
        <form className="form" onSubmit={handleSubmit}>
            <label>
            Package Name
            <input
                value={package_name}
                onChange={(e) => setPackageName(e.target.value)}
            />
            </label>

            <label>
            Severity
            <input
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
            />
            </label>

            <button className="btn primary" type="submit">
            Update Record
            </button>
        </form>
        </div>
    </div>
    );
}