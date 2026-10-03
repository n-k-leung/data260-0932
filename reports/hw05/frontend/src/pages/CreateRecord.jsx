import React, { useState } from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import { createVul } from "../redux/vulSlice.js";
export default function CreateRecord({ onAdd }) {
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const [package_name, setPackageName] = useState("");
    const [severity, setSeverity] = useState("");
    const [vulcode, setVulcode] = useState("");
    const [vendorId, setVendorId] = useState("");
    const [error, setError] = useState("");

    async function handleSubmit(e) {
        e.preventDefault();
        setError("")
        try {
            await dispatch(createVul({
                package_name: package_name,
                severity: severity,
                vul_code: vulcode,
                vendor_id: Number(vendorId),
            }));
            navigate("/");
        } catch (err) {
            setError("Cannot add new vulnerability record. Please chenck input fields");
        }
        // await onAdd({ package_name: package_name, severity:severity });
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
            Add Record
            </button>
        </form>
        </div>
    </div>
    );
}