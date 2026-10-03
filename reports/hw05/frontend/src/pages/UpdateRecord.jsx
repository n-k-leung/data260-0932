import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchVulById } from "../api/vulApi.js";
import { useDispatch } from "react-redux";
import { updateVul } from "../redux/vulSlice.js";

export default function UpdateRecord({ onUpdate }) {
  const { id } = useParams();
  const recordId = Number(id);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [package_name, setPackageName] = useState("");
  const [severity, setSeverity] = useState("");
  const [vulcode, setVulcode] = useState("");
  const [vendorId, setvendorId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const record = await fetchVulById(recordId);
        setPackageName(record.package_name);
        setSeverity(record.severity);
        setCveId(record.vulcode);
        setvendorId(record.vendorId);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, [recordId]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("")
    try{
      await dispatch(updateVul({
        id: recordId,
        data: {
          package_name: packageName,
          severity: severity,
          vul_code: vulcode,
          vendor_id: Number(vendorId),
        },
      }));
      navigate("/");
    } catch (err){
      setError("Cannot update record, check input fields")
    }
    // await onUpdate(recordId, { package_name, severity });
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

            <label>
            Vulnerability Code
            <input
                value={vulcode}
                onChange={(e) => setVulcode(e.target.value)}
            />
            </label>

            <label>
            Vendor ID
            <input
                type="number"
                value={vendorId}
                onChange={(e) => setVendorId(e.target.value)}
            />
            </label>
            {error && <div className="notice">{error}</div>}
            <button className="btn primary" type="submit">
            Update Record
            </button>
        </form>
        </div>
    </div>
    );
}