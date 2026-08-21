// ===========================
// Loading
// ===========================

const loadingStartTime = performance.now();

/**
 * Hide the initial loading screen.
 *
 * @param {number} minDuration Minimum display time (ms)
 */
export function hideLoading(minDuration = 500) {

    const loading = document.getElementById("loading-screen");

    if (!loading) return;

    const elapsed = performance.now() - loadingStartTime;
    const delay = Math.max(0, minDuration - elapsed);

    window.setTimeout(() => {

        loading.classList.add("hide");

        loading.addEventListener(
            "transitionend",
            () => loading.remove(),
            { once: true }
        );

    }, delay);

}
