const loginForm = document.getElementById("loginForm");

function goToDashboard() {
    window.location.href = "index.html";
}

if (loginForm) {
    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value.trim();
        const message = document.getElementById("loginMessage");
        const submitBtn = loginForm.querySelector("button[type='submit']");

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

        submitBtn.disabled = true;
        message.textContent = "Signing in...";
        message.className = "login-message";

        try {
            const data = await window.plagifyApi.login(email, password);
            window.plagifyApi.saveSession(data);
            message.textContent = "Login successful. Opening dashboard...";
            message.className = "login-message success";
            setTimeout(goToDashboard, 600);
        } catch (error) {
            message.textContent = error.message || "Login failed.";
            message.className = "login-message error";
            submitBtn.disabled = false;
        }
    });
}

/* New users go to the dedicated registration page (registration.html). */

const showPasswordBtn = document.getElementById("showPassword");
if (showPasswordBtn) {
    showPasswordBtn.addEventListener("click", function () {
        const input = document.getElementById("password");
        if (!input) return;
        const showing = input.type === "text";
        input.type = showing ? "password" : "text";
        showPasswordBtn.textContent = showing ? "Show" : "Hide";
    });
}
