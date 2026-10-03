import { configureStore } from "@reduxjs/toolkit";
import vulsReducer from "./vulSlice.js";

export const store = configureStore({
    reducer: {
        vuls: vulsReducer,
    },
});