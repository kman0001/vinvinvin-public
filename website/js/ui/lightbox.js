// ===========================
// Lightbox
// ===========================

export function initLightbox() {

    const lightbox = document.getElementById("lightbox");
    const image = document.getElementById("lightbox-image");
    const close = document.querySelector(".lightbox-close");

    if (!lightbox || !image || !close) {
        return;
    }

    // 이미지 클릭
    document.addEventListener("click", event => {

        const target = event.target;

        if (!(target instanceof HTMLImageElement)) {
            return;
        }

        if (!target.classList.contains("wine-image")) {
            return;
        }

        image.src = target.dataset.image || target.src;
        image.alt = target.alt;

        lightbox.classList.add("show");

    });

    // 닫기 버튼
    close.addEventListener("click", hideLightbox);

    // 배경 클릭
    lightbox.addEventListener("click", event => {

        if (event.target === lightbox) {
            hideLightbox();
        }

    });

    // ESC 키
    document.addEventListener("keydown", event => {

        if (event.key === "Escape") {
            hideLightbox();
        }

    });

    function hideLightbox() {

        lightbox.classList.remove("show");
        image.removeAttribute("src");
        image.removeAttribute("alt");

    }

}
