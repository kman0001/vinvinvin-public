import { fetchData } from "./api/api.js";
import { showMenu } from "./menu/menu.js";
import { showNotice } from "./ui/notice.js";
import { initLightbox } from "./ui/lightbox.js";
import { hideLoading } from "./ui/loading.js";

// ===========================
// Initialize
// ===========================

async function init() {
    try {
        const { menu, notice } = await fetchData();

        render(menu, notice);

    } catch (error) {
        console.error("초기화 실패:", error);

        showError();

    } finally {
        hideLoading();
    }
}

// ===========================
// Render
// ===========================

function render(menu, notice) {
    showNotice(notice);

    showMenu(menu);

    initLightbox();
}

// ===========================
// Error
// ===========================

function showError() {
    document.getElementById("menu").innerHTML = `
        <p style="text-align:center;">
            메뉴를 불러오지 못했습니다.
        </p>
    `;
}

init();
