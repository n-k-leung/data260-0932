import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

const API = "http://localhost:8032";


export const fetchVuls = createAsyncThunk(
    "vuls/fetch",
    async () => {
        const res = await axios.get(`${API}/vuls`, { withCredentials: true });
        return res.data;
    }
);

export const createVul = createAsyncThunk(
    "vuls/create",
    async (newRecord) => {
        const res = await axios.post(`${API}/vuls`, newRecord, { withCredentials: true });
        return res.data;
    }
);

export const updateVul = createAsyncThunk(
    "vuls/update",
    async ({ id, data }) => {
        const res = await axios.put(`${API}/vuls/${id}`, data, { withCredentials: true });
        return res.data;
    }
);

export const deleteVul = createAsyncThunk(
    "vuls/delete",
    async (id) => {
    await axios.delete(`${API}/vuls/${id}`, { withCredentials: true });
        return id;
    }
);
const vulSlice = createSlice({
    name: "vulnerabilities",
    initialState: {items: [], loading: false, error: null },
    reducers: {},
    extraReducers: (builder) => {
    builder
        // fetch: show loading, then fill items with the list from the server
        .addCase(fetchVuls.pending, (state) => {
            state. loading = true;
            state.error = null;
        })
        .addCase(fetchVuls.fulfilled, (state, action) => {
            state.loading = false;
            state.items = action.payload;
        })
        .addCase(fetchVuls.rejected, (state, action) => {
            state.loading = false;
            state.error = action.error.message;
        })
        // create: add the new record returned by the server to the list
        .addCase(createVul.fulfilled, (state, action) => {
            state.items.push(action.payload);
        })
        .addCase(createVul.rejected, (state, action) => {
            state.error = action.error.message;
        })
        // update: replace the old record with the updated one
        .addCase(updateVul.fulfilled, (state, action) => {
            const i = state.items.findIndex((r) => r.id === action.payload.id);
            if (i !== -1) state.items[i] = action.payload;
        })
        .addCase(updateVul.rejected, (state, action) => {
            state.error=action.error.message;
        })
        // delete: remove the record with the matching id
        .addCase(deleteVul.fulfilled, (state, action) => {
            state.items = state.items.filter((r) => r.id !== action.payload);
        })
        .addCase(deleteVul.rejected, (state, action) => {
            state.error=action.error.message;
        });
    },
});

export default vulSlice.reducer;