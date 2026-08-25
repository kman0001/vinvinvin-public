import { CATEGORY_ORDER } from "../config/constants.js";

import { createMenuCard } from "./card.js";

import {
    createNavigation,
    initNavigationObserver
} from "./navigation.js";

import {
    isAvailable,
    toPrice
} from "../utils/utils.js";

// ===========================
// Group
// ===========================

function groupByCategory(data) {

    const grouped = {};

    data.forEach(item => {

        const category = item["항목"];

        if (!grouped[category]) {
            grouped[category] = [];
        }

        grouped[category].push(item);

    });

    return grouped;

}

// ===========================
// Sort
// ===========================

function sortCategory(items) {

    // ===========================
    // 1. 판매중 / 품절 분리
    // ===========================

    const available = [];
    const soldOut = [];

    items.forEach((item, originalIndex) => {

        const entry = {
            item,
            originalIndex
        };

        if (isAvailable(item["판매 여부"])) {
            available.push(entry);
        } else {
            soldOut.push(entry);
        }

    });

    // ===========================
    // 2. 정렬번호 유무에 따라 분리
    // ===========================

    const positioned = [];
    const unsorted = [];

    available.forEach(entry => {

        const sort = Number(entry.item["정렬"]);

        if (
            Number.isFinite(sort) &&
            sort > 0
        ) {
            positioned.push({
                ...entry,
                sort
            });
        } else {
            unsorted.push(entry);
        }

    });

    // ===========================
    // 3. 정렬번호 순
    // 동일 번호 → 시트 순서
    // ===========================

    positioned.sort((a, b) => {

        if (a.sort !== b.sort) {
            return a.sort - b.sort;
        }

        return a.originalIndex - b.originalIndex;

    });

    // ===========================
    // 4. 정렬번호 없는 메뉴
    // 가격순
    // 동일 가격 → 시트 순서
    // ===========================

    unsorted.sort((a, b) => {

        const priceA = toPrice(a.item["가격"]);
        const priceB = toPrice(b.item["가격"]);

        if (priceA !== priceB) {
            return priceA - priceB;
        }

        return a.originalIndex - b.originalIndex;

    });

    // ===========================
    // 5. 판매중 메뉴 슬롯
    // ===========================

    const result = new Array(available.length);
    const overflow = [];

    // ===========================
    // 6. 정렬번호 메뉴 배치
    //
    // 정렬번호 = 판매중 메뉴 기준 위치
    //
    // 범위를 벗어나면 overflow 처리
    // ===========================

    positioned.forEach(entry => {

        const index = entry.sort - 1;

        // 범위를 벗어나면 뒤쪽에 배치
        if (index >= result.length) {
            overflow.push(entry);
            return;
        }

        // 해당 위치가 비어 있으면 배치
        if (result[index] === undefined) {
            result[index] = entry.item;
            return;
        }

        // 같은 정렬번호로 충돌하면
        // 다음 빈 슬롯을 찾음
        let nextIndex = index + 1;

        while (
            nextIndex < result.length &&
            result[nextIndex] !== undefined
        ) {
            nextIndex++;
        }

        if (nextIndex < result.length) {
            result[nextIndex] = entry.item;
        } else {
            overflow.push(entry);
        }

    });

    // ===========================
    // 7. 정렬번호 없는 메뉴
    // 남은 슬롯을 가격순으로 채움
    // ===========================

    let unsortedIndex = 0;

    for (let i = 0; i < result.length; i++) {

        if (
            result[i] === undefined &&
            unsortedIndex < unsorted.length
        ) {
            result[i] = unsorted[unsortedIndex++].item;
        }

    }

    // ===========================
    // 8. 정렬번호 없는 메뉴가 남으면
    // overflow 앞에 추가
    // ===========================

    while (unsortedIndex < unsorted.length) {

        overflow.push(
            unsorted[unsortedIndex++]
        );

    }

    // ===========================
    // 9. 범위를 초과한 정렬번호
    //
    // 정렬번호 순으로 뒤쪽에 추가
    // ===========================

    overflow.forEach(entry => {

        result.push(entry.item);

    });

    // ===========================
    // 10. 품절 메뉴
    //
    // 가격순
    // 동일 가격 → 시트 순서
    //
    // 정렬번호와 관계없이 항상 마지막
    // ===========================

    soldOut.sort((a, b) => {

        const priceA = toPrice(a.item["가격"]);
        const priceB = toPrice(b.item["가격"]);

        if (priceA !== priceB) {
            return priceA - priceB;
        }

        return a.originalIndex - b.originalIndex;

    });

    // ===========================
    // 11. 최종
    //
    // 판매중 → 품절
    // ===========================

    items.splice(
        0,
        items.length,
        ...result.filter(item => item !== undefined),
        ...soldOut.map(entry => entry.item)
    );
}

// ===========================
// Category Section
// ===========================

function createCategorySection(category) {

    const section = document.createElement("section");

    section.className = "category";
    section.id = `category-${category}`;

    section.innerHTML = `
        <h2>${category}</h2>
    `;

    return section;

}

// ===========================
// Menu
// ===========================

export function showMenu(data) {

    const menu = document.getElementById("menu");

    menu.innerHTML = "";

    const grouped = groupByCategory(data);

    const categories = CATEGORY_ORDER.filter(
        category => grouped[category]
    );

    createNavigation(categories);

    categories.forEach(category => {

        sortCategory(grouped[category]);

        const section = createCategorySection(category);

        grouped[category].forEach(item => {

            section.appendChild(
                createMenuCard(item, category)
            );

        });

        menu.appendChild(section);

    });

    initNavigationObserver();

}
