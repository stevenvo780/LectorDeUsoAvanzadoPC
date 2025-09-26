export function formatBytes(value) {
    if (!value && value !== 0) return "--";
    const units = ["B", "KB", "MB", "GB", "TB", "PB"];
    let size = Math.abs(value);
    let unit = 0;
    while (size >= 1024 && unit < units.length - 1) {
        size /= 1024;
        unit += 1;
    }
    const sign = value < 0 ? "-" : "";
    return `${sign}${size.toFixed(size >= 100 ? 0 : 1)} ${units[unit]}`;
}

export function formatNumber(value) {
    if (value === null || value === undefined) return "--";
    return Number(value).toLocaleString();
}

export function formatFrequency(value) {
    if (!value && value !== 0) return "--";
    return `${value.toFixed(0)} MHz`;
}

export function formatDuration(seconds) {
    if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
        return "--";
    }
    const total = Math.max(0, Math.floor(Number(seconds)));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    return `${hours.toString().padStart(2, "0")}h ${minutes
        .toString()
        .padStart(2, "0")}m ${secs.toString().padStart(2, "0")}s`;
}
