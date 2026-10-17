(function () {
  const form = document.getElementById("registerForm");
  if (!form) return;

  const usernameEl = document.getElementById("regUsername");
  const emailEl = document.getElementById("regEmail");
  const passwordEl = document.getElementById("regPassword");
  const confirmEl = document.getElementById("regConfirm");
  const message = document.getElementById("regMessage");
  const submitBtn = document.getElementById("regSubmitBtn");
  const fileInput = document.getElementById("regPictureInput");
  const preview = document.getElementById("regAvatarPreview");
  const chooseBtn = document.getElementById("regChoosePhoto");
  const removeBtn = document.getElementById("regRemovePhoto");

  let pictureDataUrl = null;

  function setPreview(dataUrl, initials) {
    if (!preview) return;
    if (dataUrl) {
      preview.style.backgroundImage = `url(${dataUrl})`;
      preview.textContent = "";
      preview.classList.add("has-photo");
    } else {
      preview.style.backgroundImage = "";
      preview.classList.remove("has-photo");
      preview.textContent = (initials || "?").slice(0, 2).toUpperCase();
    }
  }

  usernameEl?.addEventListener("input", function () {
    if (!pictureDataUrl) {
      const v = usernameEl.value.trim();
      setPreview(null, v || "?");
    }
  });

  chooseBtn?.addEventListener("click", function () {
    fileInput?.click();
  });

  removeBtn?.addEventListener("click", function () {
    pictureDataUrl = null;
    if (fileInput) fileInput.value = "";
    setPreview(null, usernameEl?.value.trim() || "?");
    if (removeBtn) removeBtn.hidden = true;
  });

  fileInput?.addEventListener("change", function () {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      message.textContent = "Please choose an image file.";
      message.className = "login-message error";
      return;
    }
    if (file.size > 500 * 1024) {
      message.textContent = "Image must be under 500 KB.";
      message.className = "login-message error";
      return;
    }
    const reader = new FileReader();
    reader.onload = function () {
      pictureDataUrl = reader.result;
      setPreview(pictureDataUrl);
      if (removeBtn) removeBtn.hidden = false;
      message.textContent = "";
      message.className = "login-message";
    };
    reader.onerror = function () {
      message.textContent = "Could not read the image.";
      message.className = "login-message error";
    };
    reader.readAsDataURL(file);
  });

  function wireShow(btnId, inputId) {
    const btn = document.getElementById(btnId);
    const input = document.getElementById(inputId);
    if (!btn || !input) return;
    btn.addEventListener("click", function () {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.textContent = showing ? "Show" : "Hide";
    });
  }
  wireShow("regShowPassword", "regPassword");
  wireShow("regShowConfirm", "regConfirm");

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const name = (usernameEl?.value || "").trim();
    const email = (emailEl?.value || "").trim();
    const password = passwordEl?.value || "";
    const confirm = confirmEl?.value || "";

    if (name.length < 2) {
      message.textContent = "Username must be at least 2 characters.";
      message.className = "login-message error";
      return;
    }
    if (!email.includes("@") || !email.includes(".")) {
      message.textContent = "Please enter a valid email address.";
      message.className = "login-message error";
      return;
    }
    if (password.length < 6) {
      message.textContent = "Password must be at least 6 characters.";
      message.className = "login-message error";
      return;
    }
    if (password !== confirm) {
      message.textContent = "Passwords do not match.";
      message.className = "login-message error";
      return;
    }

    if (submitBtn) submitBtn.disabled = true;
    message.textContent = "Creating your account…";
    message.className = "login-message";

    try {
      const data = await window.plagifyApi.register({
        email,
        password,
        name,
        picture: pictureDataUrl,
      });
      window.plagifyApi.saveSession(data);
      message.textContent = "Account created. Opening dashboard…";
      message.className = "login-message success";
      setTimeout(function () {
        window.location.href = "index.html";
      }, 600);
    } catch (error) {
      message.textContent = error.message || "Registration failed.";
      message.className = "login-message error";
      if (submitBtn) submitBtn.disabled = false;
    }
  });
})();
