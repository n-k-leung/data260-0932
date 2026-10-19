import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useParams } from "react-router-dom";
import { fetchVulById } from "../api/vulApi.js";
import { useDispatch } from "react-redux";
import { deleteVul } from "../redux/vulSlice.js";

export default function DeleteRecord({}) {
  const { id } = useParams();
  const recordId = Number(id);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchVulById(recordId);
        setRecord(data);
      } catch {
        setRecord(null);
      }
    })();
  }, [recordId]);

  async function handleDelete() {
    // await onDelete(recordId);
    setError("")
    try {
      await dispatch(deleteVul(recordId));
      navigate("/")
    } catch(err){
      setError("Cannot delete record")
    }
  }

  return (
    <div className="card">
        <div className="card-header">
        <div className="page-title">Delete Record</div>
        </div>

        <div className="card-body">
        {record ? (
            <>
            <p style={{ fontSize: "18px", marginBottom: "24px" }}>
                Are you sure you want to delete <strong>{record.package_name}</strong> ({record.severity})?
            </p>
            {error && <div className="notice">{error}</div>}
            <button className="btn danger" onClick={handleDelete}>
                Delete record
            </button>
            </>
        ) : (
            <div className="notice">
            record not found (or already deleted).
            </div>
        )}
        </div>
    </div>
    );
}