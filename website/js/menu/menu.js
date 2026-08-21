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

    const result = new Array(items.length);
    const unsorted = [];

    // ===========================
    // 1. 정렬값이 있는 메뉴를 슬롯에 배치
    // ===========================

    items.forEach(item => {

        const sort = Number(item["정렬"]);

        // 정렬값이 없으면 나중에 처리
        if (!Number.isFinite(sort) || sort <= 0) {
            unsorted.push(item);
            return;
        }

        // 정렬값은 1부터 시작하는 위치
        let index = sort - 1;

        // 범위를 벗어나면 마지막 위치부터 탐색
        if (index >= result.length) {
            index = result.length - 1;
        }

        // 해당 위치가 이미 차있으면 다음 빈 슬롯 탐색
        while (
            index < result.length &&
            result[index] !== undefined
        ) {
            index++;
        }

        // 뒤쪽에 빈 슬롯이 없으면 마지막 빈 슬롯 탐색
        if (index >= result.length) {

            index = result.length - 1;

            while (
                index >= 0 &&
                result[index] !== undefined
            ) {
                index--;
            }

        }

        if (index >= 0) {
            result[index] = item;
        }

    });

    // ===========================
    // 2. 정렬값이 없는 메뉴 정렬
    //    판매 여부 → 가격
    // ===========================

    unsorted.sort((a, b) => {

        const availableA = isAvailable(a["판매 여부"]);
        const availableB = isAvailable(b["판매 여부"]);

        // 판매중 먼저
        if (availableA !== availableB) {
            return availableA ? -1 : 1;
        }

        // 가격순
        const priceA = toPrice(a["가격"]);
        const priceB = toPrice(b["가격"]);

        return priceA - priceB;

    });

    // ===========================
    // 3. 남은 슬롯을 순서대로 채움
    // ===========================

    let unsortedIndex = 0;

    for (let i = 0; i < result.length; i++) {

        if (result[i] === undefined) {
            result[i] = unsorted[unsortedIndex++];
        }

    }

    // ===========================
    // 4. 원본 배열에 반영
    // ===========================

    items.splice(0, items.length, ...result);

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
