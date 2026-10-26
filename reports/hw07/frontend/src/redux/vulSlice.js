import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import client, { errorText } from "../api/client.js";

export const fetchVuls = createAsyncThunk(
    "vuls/fetch",
    async (_, { rejectWithValue }) => {
        try {
            const res = await client.get("/vuls");
            return res.data;
        } catch (err) {
            return rejectWithValue(errorText(err));
        }
    }
);

export const createVul = createAsyncThunk(
    "vuls/create",
    async (newRecord, { rejectWithValue }) => {
        try {
            const res = await client.post("/vuls", newRecord);
            return res.data;
        } catch (err) {
            return rejectWithValue(errorText(err));
        }
    }
);

export const updateVul = createAsyncThunk(
    "vuls/update",
    async ({ id, data }, { rejectWithValue }) => {
        try {
            const res = await client.put('/vuls/${id}', data);
            return res.data;
        } catch (err) {
            return rejectWithValue(errorText(err));
        }
    }
);

export const deleteVul = createAsyncThunk(
    "vuls/delete",
    async (id, { rejectWithValue }) => {
        try {
            await client.delete('/vuls/${id}');
            return id;
        } catch (err) {
            return rejectWithValue(errorText(err));
        }
    }
);

const vulSlice = createSlice({
    name: "vulnerabilities",
    initialState: { items: [], loading: false, error: null },
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchVuls.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchVuls.fulfilled, (state, action) => {
                state.loading = false;
                state.items = action.payload;
            })
            .addCase(fetchVuls.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload || action.error.message;
            })
            .addCase(createVul.fulfilled, (state, action) => {
                state.items.push(action.payload);
            })
            .addCase(createVul.rejected, (state, action) => {
                state.error = action.payload || action.error.message;
            })
            .addCase(updateVul.fulfilled, (state, action) => {
                const i = state.items.findIndex((r) => r.id === action.payload.id);
                if (i !== -1) state.items[i] = action.payload;
            })
            .addCase(updateVul.rejected, (state, action) => {
                state.error = action.payload || action.error.message;
            })
            .addCase(deleteVul.fulfilled, (state, action) => {
                state.items = state.items.filter((r) => r.id !== action.payload);
            })
            .addCase(deleteVul.rejected, (state, action) => {
                state.error = action.payload || action.error.message;
            });
    },
});



export default vulSlice.reducer;