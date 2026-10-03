import React, { useEffect, useState } from "react";
import { fetchVendors, createVendor } from "../api/vulApi.js";

export default function Vendors({ auth }) {
    const [vendors, setVendors] = useState([]);
    const [loading, setLoading] = useState(false);

    const [name, setName] = useState("");
    const [industry, setIndustry] = useState("");
    const [contactEmail, setContactEmail] = useState("");

    async function loadVendors() {
        setLoading(true);
        const data = await fetchVendors();
        setVendors(data);
        setLoading(false);
    }
    useEffect(() => {
        if (auth.loggedIn) loadVendors();
    }, [auth. loggedIn]);

    async function handleSubmit(e) {
        e.preventDefault();
        await createVendor({ name, industry, contact_email: contactEmail });
        setName("");
        setIndustry("");
        setContactEmail("");
        loadVendors();
    }
    if (!auth.loggedIn) {
        return (
            <div className="card">
                <div className="card-header">
                    <div>
                        <div className="page-title">Vendors</div>
                        <div className="subtitle">Login first to fetch records from the protected API .</div>
                    </div>
                </div>
                <div className="card-body">
                    <div className="notice">Login required</div>
                </div>
            </div>
        );
    }
    return (
    <>
        <div className="card">
            <div className="card-header">
            <div className="page-title">Add Vendor</div>
            <div className="subtitle">The company behind a package</div>
        </div>

        <div className="card-body">
            <form className="form" onSubmit={handleSubmit}>
                <label>
                    Name
                    <input value={name} onChange={ (e) => setName(e. target.value)} />
                </label>

                <label>
                    Industry
                    <input value={industry} onChange={(e) => setIndustry(e.target.value)} />
                </label>

                <label>
                    Contact Email
                    <input
                        type="email"
                        value={contactEmail}
                        onChange={(e) => setContactEmail(e.target.value)}/>
                </label>

                <button className="btn primary" type="submit">
                    Add Vendor
                </button>
            </form>
        </div>
    </div>
        <div className="card">
            <div className="card-header">
                <div>
                    <div className="page-title">Vendors</div>
                    <div className="subtitle">
                        Use a vendor's ID when adding a vulnerability record.
                     </div>
                </div>
            </div>

            <div className="card-body">
                {loading ? (
                    <div className="notice">Loading records ...</div>
                ) : vendors.length === 0 ? (
                    <div className="notice">No vendors found. Use the form above to add one.</div>
                ): (
                    <div className="table-wrap">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Name</th>
                                    <th>Industry</th>
                                    <th>Contact Email</th>
                                </tr>
                            </thead>

                            <tbody>
                                {vendors.map((v) => (
                                <tr key={v.id}>
                                <td>{v.id}</td>
                                <td>{v.name}</td>
                                <td>{v.industry}</td>
                                <td>{v.contact_email}</td>
                            </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                )}
                </div>
            </div>
        </>
        );
    }