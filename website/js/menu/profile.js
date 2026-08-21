// ===========================
// Wine Profile
// ===========================

const PROFILE_ICONS = {
    "당도": "🍬",
    "산도": "🍋",
    "바디": "💪",
    "탄닌": "🌿"
};

const PROFILE_ORDER = [
    "당도",
    "산도",
    "바디",
    "탄닌"
];

export function renderWineProfile(profile) {

    const values = {};

    profile.forEach(item => {

        const match = item.match(/(당도|산도|바디|탄닌)\s*(\d)/);

        if (match) {
            values[match[1]] = Number(match[2]);
        }

    });

    return PROFILE_ORDER.map(label => {

        const level = values[label];

        if (level === undefined) {
            return "";
        }

        const bars = Array.from(
            { length: 5 },
            (_, i) =>
                `<span class="bar ${i < level ? "fill" : "empty"}"></span>`
        ).join("");

        return `
            <span class="profile-tag">
                <span class="profile-icon">${PROFILE_ICONS[label]}</span>
                <span class="profile-label">${label}</span>
                <span class="profile-bars">${bars}</span>
            </span>
        `;

    }).join("");

}
