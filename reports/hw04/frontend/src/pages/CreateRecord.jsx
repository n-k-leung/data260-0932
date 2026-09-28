import React, { useState } from "react";

export default function CreateRecord({ onAdd }) {
  const [package_name, setPackageName] = useState("");
  const [severity, setSeverity] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    await onAdd({ package_name: package_name, severity:severity });
  }

  return (
    <div className="card">
        <div className="card-header">
        <div className="page-title">Add Record</div>
        <div className="subtitle">Enter record details below</div>
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
            Add Record
            </button>
        </form>
        </div>
    </div>
    );
}