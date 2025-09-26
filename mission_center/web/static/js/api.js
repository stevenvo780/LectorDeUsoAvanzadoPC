const DEFAULT_TIMEOUT = 5000;
const DEFAULT_HEADERS = {
    Accept: "application/json",
    "Content-Type": "application/json",
};

export async function fetchJSON(url, { timeout = DEFAULT_TIMEOUT, headers = {}, cache = "no-store", ...init } = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            cache,
            signal: controller.signal,
            headers: {
                ...DEFAULT_HEADERS,
                ...headers,
            },
            ...init,
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
            error.status = response.status;
            throw error;
        }

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            throw new Error("Response is not JSON");
        }

        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);
        if (error?.name === "AbortError") {
            const timeoutError = new Error("Request timeout");
            timeoutError.code = "timeout";
            throw timeoutError;
        }
        throw error;
    }
}

export async function fetchDashboardData() {
    return Promise.all([fetchJSON("/api/current"), fetchJSON("/api/history")]);
}
