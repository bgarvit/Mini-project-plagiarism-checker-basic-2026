const loginForm = document.getElementById("loginForm");

if (loginForm) {

  loginForm.addEventListener("submit", function (event) {

    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    const message = document.getElementById("loginMessage");

    if (!email || !password) {

      message.textContent =
        "Please enter your email and password.";

      message.className = "login-message error";

      return;
    }


    /*
      FRONTEND DEMO LOGIN

      Any valid email + password
      will successfully enter the application.
    */

    message.textContent =
      "Login successful. Opening ScanForge...";

    message.className = "login-message success";


    /*
      Save login state.
    */

    localStorage.setItem(
      "scanforgeLoggedIn",
      "true"
    );

    localStorage.setItem(
      "scanforgeUser",
      email
    );


    /*
      Open main plagiarism checker.
    */

    setTimeout(function () {

      window.location.href = "checker.html";

    }, 700);

  });

}


/* ==========================================
   SHOW / HIDE PASSWORD
   ========================================== */

const showPassword =
  document.getElementById("showPassword");

if (showPassword) {

  showPassword.addEventListener("click", function () {

    const password =
      document.getElementById("password");

    if (password.type === "password") {

      password.type = "text";

      showPassword.textContent = "Hide";

    } else {

      password.type = "password";

      showPassword.textContent = "Show";

    }

  });

}


/* ==========================================
   FORGOT PASSWORD
   ========================================== */

const forgotPassword =
  document.getElementById("forgotPassword");

if (forgotPassword) {

  forgotPassword.addEventListener("click", function (event) {

    event.preventDefault();

    alert(
      "Password recovery will be available when a backend authentication system is connected."
    );

  });

}


/* ==========================================
   PROTECT CHECKER PAGE
   ========================================== */

if (
  window.location.pathname.endsWith("checker.html")
) {

  const loggedIn =
    localStorage.getItem("scanforgeLoggedIn");

  if (loggedIn !== "true") {

    window.location.href = "login.html";

  }

}


/* ==========================================
   LOGOUT
   ========================================== */

const logoutBtn =
  document.getElementById("logoutBtn");

if (logoutBtn) {

  logoutBtn.addEventListener("click", function () {

    localStorage.removeItem(
      "scanforgeLoggedIn"
    );

    localStorage.removeItem(
      "scanforgeUser"
    );

    window.location.href = "index.html";

  });

}

const STORAGE_KEY = "scanforge_statistics";

const defaultStats = {
    totalChecks: 0,
    documentsScannedToday: 0
};

function getStatistics() {
    const saved = localStorage.getItem(STORAGE_KEY);

    if (!saved) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultStats));
        return { ...defaultStats };
    }

    try {
        return {
            ...defaultStats,
            ...JSON.parse(saved)
        };
    } catch {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultStats));
        return { ...defaultStats };
    }
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

    saveStatistics(stats);
    updateStatisticsUI();
}

document.addEventListener("DOMContentLoaded", () => {
    updateStatisticsUI();
});