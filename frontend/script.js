const loginForm = document.getElementById("loginForm");

if (loginForm) {
    loginForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value.trim();
        const message = document.getElementById("loginMessage");

        if (!email || !password) {
            message.textContent = "Please enter your email and password.";
            message.className = "login-message error";
            return;
        }

        if (!email.includes("@") || !email.includes(".")) {
            message.textContent = "Please enter a valid email address.";
            message.className = "login-message error";
            return;
        }

        if (password.length < 6) {
            message.textContent = "Password must contain at least 6 characters.";
            message.className = "login-message error";
            return;
        }

        message.textContent = "Login successful. Opening Plagify...";
        message.className = "login-message success";

        localStorage.setItem("plagifyLoggedIn", "true");
        localStorage.setItem("plagifyUser", email);

        setTimeout(function () {
            window.location.href = "index.html";
        }, 700);
    });
}

const showPassword = document.getElementById("showPassword");

if (showPassword) {
    showPassword.addEventListener("click", function () {
        const password = document.getElementById("password");

        if (!password) return;

        if (password.type === "password") {
            password.type = "text";
            showPassword.textContent = "Hide";
        } else {
            password.type = "password";
            showPassword.textContent = "Show";
        }
    });
}

const forgotPassword = document.getElementById("forgotPassword");

if (forgotPassword) {
    forgotPassword.addEventListener("click", function (event) {
        event.preventDefault();

        const message = document.getElementById("loginMessage");

        if (message) {
            message.textContent = "Password recovery requires a backend authentication system.";
            message.className = "login-message error";
        }
    });
}

const logoutBtn = document.getElementById("logoutBtn");

if (logoutBtn) {
    logoutBtn.addEventListener("click", function () {
        localStorage.removeItem("plagifyLoggedIn");
        localStorage.removeItem("plagifyUser");
        window.location.href = "introduction.html";
    });
}

const currentPage = window.location.pathname.split("/").pop().toLowerCase();

if (
    currentPage === "index.html" ||
    currentPage === "" ||
    currentPage === "/"
) {
    const loggedIn = localStorage.getItem("plagifyLoggedIn");

    if (loggedIn !== "true") {
        window.location.replace("introduction.html");
    }
}

const STORAGE_KEY = "plagify_statistics";

const defaultStats = {
    totalChecks: 0,
    documentsScannedToday: 0,
    lastScanDate: ""
};

function getToday() {
    const date = new Date();

    return [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getDate()).padStart(2, "0")
    ].join("-");
}

function getStatistics() {
    let stats;

    try {
        stats = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch {
        stats = {};
    }

    stats = {
        ...defaultStats,
        ...stats
    };

    const today = getToday();

    if (stats.lastScanDate !== today) {
        stats.documentsScannedToday = 0;
        stats.lastScanDate = today;
        saveStatistics(stats);
    }

    return stats;
}

function saveStatistics(stats) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stats));
}

function updateStatisticsUI() {
    const stats = getStatistics();

    const totalChecks = document.getElementById("totalChecksRun");
    const documentsToday = document.getElementById("documentsScannedToday");
    const documentsScanned = document.getElementById("documentsScanned");

    if (totalChecks) {
        totalChecks.textContent = stats.totalChecks.toLocaleString();
    }

    if (documentsToday) {
        documentsToday.textContent = stats.documentsScannedToday.toLocaleString();
    }

    if (documentsScanned) {
        documentsScanned.textContent = stats.documentsScannedToday.toLocaleString();
    }
}

function recordSuccessfulScan() {
    const stats = getStatistics();

    stats.totalChecks += 1;
    stats.documentsScannedToday += 1;
    stats.lastScanDate = getToday();

    saveStatistics(stats);
    updateStatisticsUI();
}

window.getStatistics = getStatistics;
window.recordSuccessfulScan = recordSuccessfulScan;

document.addEventListener("DOMContentLoaded", function () {
    updateStatisticsUI();
});