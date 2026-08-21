// ===========================
// Navigation
// ===========================

export function createNavigation(categories) {

    const nav = document.getElementById("category-nav");

    nav.innerHTML = "";

    categories.forEach(category => {

        const button = document.createElement("button");

        button.className = "nav-button";
        button.textContent = category;

        button.addEventListener("click", () => {

            document
                .getElementById(`category-${category}`)
                ?.scrollIntoView({
                    behavior: "smooth"
                });

        });

        nav.appendChild(button);

    });

}

// ===========================
// Active Navigation
// ===========================

export function initNavigationObserver() {

    const buttons = document.querySelectorAll(".nav-button");
    const sections = document.querySelectorAll(".category");

    if (!buttons.length || !sections.length) {
        return;
    }

    function updateActiveNavigation() {

        const nav = document.getElementById("category-nav");
        const navHeight = nav ? nav.offsetHeight : 0;

        let currentSection = sections[0];

        sections.forEach(section => {

            const sectionTop =
                section.getBoundingClientRect().top;

            if (sectionTop <= navHeight + 20) {
                currentSection = section;
            }

        });

        const activeId = currentSection.id;

        buttons.forEach(button => {

            const targetId =
                `category-${button.textContent.trim()}`;

            button.classList.toggle(
                "active",
                targetId === activeId
            );

        });

    }

    window.addEventListener(
        "scroll",
        updateActiveNavigation,
        { passive: true }
    );

    updateActiveNavigation();

}
