import { API } from "../config/constants.js";

// ===========================
// Fetch Data
// ===========================

export async function fetchData() {

    const response = await fetch(API, {
        cache: "no-store"
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();

}
