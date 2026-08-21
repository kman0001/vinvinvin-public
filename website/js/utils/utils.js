import { NO_IMAGE } from "../config/constants.js";

// ===========================
// String
// ===========================

export function splitText(value, separator = "/") {

    return String(value || "")
        .split(separator)
        .map(item => item.trim())
        .filter(Boolean);

}

// ===========================
// Image
// ===========================

export function getImageSrc(image) {

    const file = String(image || "").trim();

    if (!file) {
        return NO_IMAGE;
    }

    return /^(https?:)?\/\//i.test(file)
        ? file
        : `images/${file}`;

}

// ===========================
// Menu Status
// ===========================

export function isAvailable(value) {

    const status = String(value).trim().toUpperCase();

    return status !== "FALSE" && status !== "품절";

}

export function isRecommended(value) {

    return String(value).trim().toUpperCase() === "추천";

}

// ===========================
// Price
// ===========================

export function toPrice(value) {

    return Number(value) || 0;

}

export function formatPrice(value) {

    return `₩${toPrice(value).toLocaleString("ko-KR")}`;

}

// ===========================
// Extra Icon
// ===========================

export function getExtraIcon(value) {

    const text = String(value || "").trim();

    if (/^\d{4}$/.test(text) || text.toUpperCase() === "NV") {
        return "📅";
    }

    if (/ml/i.test(text)) {
        return "🥂";
    }

    return "📌";

}
