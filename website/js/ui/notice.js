// ===========================
// Notice Sections
// ===========================

const NOTICE_SECTIONS = [
    {
        type: "안내",
        title: "",
        icon: "•"
    },
    {
        type: "주의",
        title: "⚠️ 주의",
        icon: "•"
    },
    {
        type: "이벤트",
        title: "🎉 이벤트",
        icon: "•"
    },
    {
        type: "기타",
        title: "ℹ️ 기타",
        icon: "•"
    }
];

// ===========================
// Notice
// ===========================

export function showNotice(data) {

    const notice = document.getElementById("notice");

    if (!notice || !data.length) {
        return;
    }

    const items = data
        .filter(item => String(item["내용"]).trim() !== "")
        .sort((a, b) => Number(a["정렬"]) - Number(b["정렬"]));

    const title =
        items.find(item => item["항목"] === "제목")?.["내용"] || "안내";

    let html = `
        <div class="notice-box">
            <div class="notice-title">${title}</div>
    `;

    NOTICE_SECTIONS.forEach(section => {

        const sectionItems = items.filter(
            item => item["항목"] === section.type
        );

        if (!sectionItems.length) {
            return;
        }

        if (section.title) {

            html += `
                <div class="notice-warning">
                    <h3>${section.title}</h3>
                    <ul class="notice-list">
            `;

        } else {

            html += `<ul class="notice-list">`;

        }

        sectionItems.forEach(item => {

            html += `
                <li>${section.icon} ${item["내용"]}</li>
            `;

        });

        html += `</ul>`;

        if (section.title) {
            html += `</div>`;
        }

    });

    html += `</div>`;

    notice.innerHTML = html;

}
