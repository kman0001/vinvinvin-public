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

export function getImageSrc(image, fallback = NO_IMAGE) {
    const file = String(image || "").trim();

    if (!file) {
        return fallback;
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

export function isEvent(value) {

    return String(value).trim().toUpperCase() === "이벤트";

}

export function formatQuotedText(value) {

    return String(value || "")
        .replace(/"([^"]*)"/g, '<span class="bold-quotes">"$1"</span>');

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

export function formatDiscountPrice(normalPrice, discountPrice) {

    const normal = toPrice(normalPrice);
    const discounted = toPrice(discountPrice);

    if (normal > 0 && discounted > 0) {
        return `
            <span class="normal-price">${formatPrice(normal)}</span>
            <span class="discount-price">${formatPrice(discounted)}</span>
            <span class="badge badge-discount">할인</span>
        `;
    }

    return formatPrice(normalPrice);

}

// ===========================
// Extra Icon
// ===========================

export function getExtraIcon(value) {
    const text = String(value ?? "").trim();

    if (/^\d{4}$/.test(text) || text.toUpperCase() === "NV") {
        return "📅";
    }

    if (/ml/i.test(text)) {
        return "🧪";
    }

    if (/^\d+\s*IBU$/i.test(text)) {
        return `<img src="images/icons/ibu.svg" alt="IBU" class="extra-icon">`;
    }

    return "📌";
}
