import React from "react";
import { Link } from "react-router-dom";

export default function Home({ records, loading, auth }) {
  // If not logged in, show a clear message (since backend is protected)
  if (!auth.loggedIn) {
    return (
      <div className="card">
        <div className="card-header">
          <div>
            <div className="page-title">Vulnerabilities</div>
            <div className="subtitle">
              Login first to fetch records from the protected API.
            </div>
          </div>
        </div>

        <div className="card-body">
          <div className="notice">
            You are not logged in. Use the Login bar above.
          </div>
        </div>
      </div>
    );
  }

  // Logged in: show vulnerabilities table
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="page-title">Vulnerabilities</div>
          <div className="subtitle">
            Session-based access: these open source vulnerabilities are fetched from FastAPI + MySQL using your cookie session.
          </div>
        </div>

        <Link className="btn primary" to="/create">
          + Add Record
        </Link>
      </div>

      <div className="card-body">
        {loading ? (
          <div className="notice">Loading records...</div>
        ) : records.length === 0 ? (
          <div className="notice">No records found. Click “Add Record”.</div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Package Name</th>
                  <th>Severity</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {records.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>{u.package_name}</td>
                    <td>{u.severity}</td>
                    <td className="actions">
                      <Link className="btn" to={`/update/${u.id}`}>
                        Update
                      </Link>
                      <Link className="btn danger" to={`/delete/${u.id}`}>
                        Delete
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}