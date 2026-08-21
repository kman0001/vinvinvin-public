import { getFlag, getTypeIcon } from "./icons.js";
import { renderWineProfile } from "./profile.js";

import {
    splitText,
    getImageSrc,
    isAvailable,
    isRecommended,
    toPrice,
    formatPrice,
    getExtraIcon
} from "../utils/utils.js";

// ===========================
// Meta Tags
// ===========================

function createMetaTags({
    country,
    variety,
    abv,
    extra,
    category
}) {

    const flag = getFlag(country);
    const typeIcon = getTypeIcon(category);
    const extraIcon = getExtraIcon(extra);

    return `
        <div class="wine-meta">

            ${country
                ? `<span class="tag">${flag} ${country}</span>`
                : ""}

            ${variety
                ? `<span class="tag">${typeIcon} ${variety}</span>`
                : ""}

            ${abv
                ? `<span class="tag">☺️ ${abv}</span>`
                : ""}

            ${extra
                ? `<span class="tag">${extraIcon} ${extra}</span>`
                : ""}

        </div>
    `;

}

// ===========================
// Price
// ===========================

function createPrice(price, available) {

    return `
        <div class="price">
            ${
                available
                    ? formatPrice(price)
                    : `<span class="soldout">SOLD OUT</span>`
            }
        </div>
    `;

}

// ===========================
// Menu Card
// ===========================

export function createMenuCard(item, category) {

    const card = document.createElement("div");
    card.className = "card";

    const imageSrc = getImageSrc(item["사진"]);

    const info = splitText(item["주요 정보 1"]);
    const profile = splitText(item["주요 정보 2"]);

    const country = info[0] || "";
    const variety = info[1] || "";
    const abv = info[2] || "";
    const extra = info[3] || "";

    const available = isAvailable(item["판매 여부"]);
    const recommended = isRecommended(item["추천"]);

    const price = toPrice(item["가격"]);

    card.innerHTML = `
        <div class="card-layout">

            <img
                class="wine-image"
                loading="lazy"
                decoding="async"
                src="${imageSrc}"
                data-image="${imageSrc}"
                alt="${item["이름"]}"
                onerror="this.src='images/no-image.webp'"
            >

            <div class="wine-info">

                <div class="name">
                    ${item["이름"]}
                    ${
                        recommended
                            ? `<span class="badge">추천</span>`
                            : ""
                    }
                </div>

                ${createMetaTags({
                    country,
                    variety,
                    abv,
                    extra,
                    category
                })}

                ${
                    profile.length
                        ? `
                        <div class="wine-profile">
                            ${renderWineProfile(profile)}
                        </div>
                        `
                        : ""
                }

                ${
                    item["설명"]
                        ? `<div class="web-desc">${
                            // 정규표현식으로 큰따옴표("") 안의 내용을 span 태그로 감쌉니다.
                            item["설명"].replace(/"([^"]*)"/g, '<span class="bold-quotes">"$1"</span>')
                          }</div>`
                        : ""
                }

                ${createPrice(price, available)}

            </div>

        </div>
    `;

    return card;

}
