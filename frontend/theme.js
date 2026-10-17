(function () {
  const STORAGE_KEY = "plagify-theme";

  function getPreferred() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }

  applyTheme(getPreferred());

  function bindToggle() {
    const btn = document.getElementById("themeToggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }

  function initials(name, email) {
    const src = (name || email || "U").trim();
    const parts = src.split(/[\s@._-]+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return src.slice(0, 2).toUpperCase();
  }

  function setAvatar(el, profile) {
    if (!el) return;
    if (profile && profile.picture) {
      el.style.backgroundImage = `url(${profile.picture})`;
      el.textContent = "";
      el.classList.add("has-photo");
    } else {
      el.style.backgroundImage = "";
      el.classList.remove("has-photo");
      el.textContent = initials(profile && profile.name, profile && profile.email);
    }
  }

  function updateAuthUI(profile) {
    const signIn = document.getElementById("signInBtn");
    const userMenu = document.getElementById("userMenu");
    const loggedIn =
      localStorage.getItem("plagifyLoggedIn") === "true" &&
      !!localStorage.getItem("plagifyToken");

    // After sign-in: fully hide the Sign in button; show the user menu instead
    if (signIn) {
      signIn.hidden = loggedIn;
      signIn.style.display = loggedIn ? "none" : "";
      if (loggedIn) {
        signIn.setAttribute("aria-hidden", "true");
      } else {
        signIn.removeAttribute("aria-hidden");
      }
    }
    if (userMenu) {
      userMenu.hidden = !loggedIn;
      userMenu.style.display = loggedIn ? "" : "none";
    }

    if (!loggedIn || !userMenu) return;

    const p =
      profile ||
      (window.plagifyApi && window.plagifyApi.getStoredProfile
        ? window.plagifyApi.getStoredProfile()
        : null) ||
      { email: localStorage.getItem("plagifyUser") || "", name: "" };

    const nameEl = document.getElementById("userName");
    const emailEl = document.getElementById("userEmail");
    const avatarEl = document.getElementById("userAvatar");
    if (nameEl) nameEl.textContent = p.name || (p.email ? p.email.split("@")[0] : "Account");
    if (emailEl) emailEl.textContent = p.email || "";
    setAvatar(avatarEl, p);
  }

  // Pending picture data URL for the open profile modal (null = unchanged, "" = remove)
  let pendingPicture = null;

  function setRemovePhotoVisible(hasPhoto) {
    const removeBtn = document.getElementById("profilePictureRemove");
    if (removeBtn) removeBtn.hidden = !hasPhoto;
  }

  function openProfileModal() {
    const modal = document.getElementById("profileModal");
    if (!modal) return;
    const p =
      (window.plagifyApi && window.plagifyApi.getStoredProfile
        ? window.plagifyApi.getStoredProfile()
        : null) || {};
    const nameInput = document.getElementById("profileNameInput");
    const emailEl = document.getElementById("profileEmail");
    const providerEl = document.getElementById("profileProvider");
    const avatarEl = document.getElementById("profileAvatar");
    const fileInput = document.getElementById("profilePictureInput");
    pendingPicture = null;
    if (fileInput) fileInput.value = "";
    if (nameInput) nameInput.value = p.name || "";
    if (emailEl) emailEl.textContent = p.email || "—";
    if (providerEl)
      providerEl.textContent = "Signed in with Email";
    setAvatar(avatarEl, p);
    setRemovePhotoVisible(!!(p && p.picture));
    const msg = document.getElementById("profileMessage");
    if (msg) {
      msg.textContent = "";
      msg.className = "login-message";
    }
    const otpMsg = document.getElementById("otpMessage");
    if (otpMsg) {
      otpMsg.textContent = "";
      otpMsg.className = "login-message";
    }
    const pwdFields = document.getElementById("passwordChangeFields");
    if (pwdFields) pwdFields.hidden = true;
    ["profileOtpInput", "profileNewPassword", "profileConfirmPassword"].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    modal.hidden = false;
  }

  function closeProfileModal() {
    const modal = document.getElementById("profileModal");
    if (modal) modal.hidden = true;
    pendingPicture = null;
    const fileInput = document.getElementById("profilePictureInput");
    if (fileInput) fileInput.value = "";
  }

  function readImageAsDataUrl(file) {
    return new Promise(function (resolve, reject) {
      if (!file || !file.type || !file.type.startsWith("image/")) {
        reject(new Error("Please choose an image file (JPEG, PNG, WebP, or GIF)."));
        return;
      }
      const maxBytes = 500 * 1024;
      if (file.size > maxBytes) {
        reject(new Error("Image is too large. Please use a file under 500 KB."));
        return;
      }
      const reader = new FileReader();
      reader.onload = function () {
        resolve(reader.result);
      };
      reader.onerror = function () {
        reject(new Error("Could not read the image file."));
      };
      reader.readAsDataURL(file);
    });
  }

  function bindUserMenu() {
    const chip = document.getElementById("userChip");
    const dropdown = document.getElementById("userDropdown");
    const profileBtn = document.getElementById("profileBtn");
    const logoutBtn = document.getElementById("logoutBtn");

    if (chip && dropdown) {
      chip.addEventListener("click", function (e) {
        e.stopPropagation();
        const open = !dropdown.hidden;
        dropdown.hidden = open;
        chip.setAttribute("aria-expanded", open ? "false" : "true");
      });
      document.addEventListener("click", function () {
        dropdown.hidden = true;
        chip.setAttribute("aria-expanded", "false");
      });
    }

    if (profileBtn) {
      profileBtn.addEventListener("click", function () {
        if (dropdown) dropdown.hidden = true;
        openProfileModal();
      });
    }

    if (logoutBtn) {
      logoutBtn.addEventListener("click", function () {
        if (window.plagifyApi && window.plagifyApi.clearToken) {
          window.plagifyApi.clearToken();
        } else {
          localStorage.removeItem("plagifyLoggedIn");
          localStorage.removeItem("plagifyUser");
          localStorage.removeItem("plagifyToken");
          localStorage.removeItem("plagifyUserProfile");
        }
        updateAuthUI(null);
        window.location.href = "index.html";
      });
    }

    const closeBtn = document.getElementById("profileModalClose");
    const cancelBtn = document.getElementById("profileCancelBtn");
    const saveBtn = document.getElementById("profileSaveBtn");
    const overlay = document.getElementById("profileModal");
    const fileInput = document.getElementById("profilePictureInput");
    const chooseBtn = document.getElementById("profilePictureChoose");
    const removeBtn = document.getElementById("profilePictureRemove");

    if (closeBtn) closeBtn.addEventListener("click", closeProfileModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeProfileModal);
    if (overlay) {
      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) closeProfileModal();
      });
    }

    if (chooseBtn && fileInput) {
      chooseBtn.addEventListener("click", function () {
        fileInput.click();
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", async function () {
        const msg = document.getElementById("profileMessage");
        const avatarEl = document.getElementById("profileAvatar");
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        try {
          const dataUrl = await readImageAsDataUrl(file);
          pendingPicture = dataUrl;
          setAvatar(avatarEl, { picture: dataUrl });
          setRemovePhotoVisible(true);
          if (msg) {
            msg.textContent = "Photo ready — click Save to apply.";
            msg.className = "login-message";
          }
        } catch (err) {
          fileInput.value = "";
          if (msg) {
            msg.textContent = err.message || "Could not load image.";
            msg.className = "login-message error";
          }
        }
      });
    }

    if (removeBtn) {
      removeBtn.addEventListener("click", function () {
        const avatarEl = document.getElementById("profileAvatar");
        const msg = document.getElementById("profileMessage");
        const stored =
          (window.plagifyApi && window.plagifyApi.getStoredProfile
            ? window.plagifyApi.getStoredProfile()
            : null) || {};
        pendingPicture = "";
        if (fileInput) fileInput.value = "";
        setAvatar(avatarEl, { name: stored.name, email: stored.email, picture: "" });
        setRemovePhotoVisible(false);
        if (msg) {
          msg.textContent = "Photo will be removed when you save.";
          msg.className = "login-message";
        }
      });
    }

    if (saveBtn) {
      saveBtn.addEventListener("click", async function () {
        const nameInput = document.getElementById("profileNameInput");
        const msg = document.getElementById("profileMessage");
        if (!window.plagifyApi) return;
        try {
          saveBtn.disabled = true;
          const payload = {
            name: nameInput ? nameInput.value.trim() : "",
          };
          if (pendingPicture !== null) {
            payload.picture = pendingPicture;
          }
          const updated = await window.plagifyApi.updateProfile(payload);
          const profile = {
            email: updated.email,
            name: updated.name,
            picture: updated.picture,
            auth_provider: updated.auth_provider,
          };
          localStorage.setItem("plagifyUserProfile", JSON.stringify(profile));
          localStorage.setItem("plagifyUser", updated.email);
          updateAuthUI(profile);
          pendingPicture = null;
          if (msg) {
            msg.textContent = "Profile saved.";
            msg.className = "login-message success";
          }
          setTimeout(closeProfileModal, 700);
        } catch (err) {
          if (msg) {
            msg.textContent = err.message || "Could not save profile.";
            msg.className = "login-message error";
          }
        } finally {
          saveBtn.disabled = false;
        }
      });
    }

    const requestOtpBtn = document.getElementById("profileRequestOtpBtn");
    const changePwdBtn = document.getElementById("profileChangePasswordBtn");
    if (requestOtpBtn) {
      requestOtpBtn.addEventListener("click", async function () {
        const otpMsg = document.getElementById("otpMessage");
        const pwdFields = document.getElementById("passwordChangeFields");
        if (!window.plagifyApi || !window.plagifyApi.requestPasswordOtp) return;
        requestOtpBtn.disabled = true;
        try {
          const res = await window.plagifyApi.requestPasswordOtp();
          let text = res.message || "OTP sent to your email.";
          if (res.demo_otp) {
            text += " Demo code (email not configured): " + res.demo_otp;
          }
          if (otpMsg) {
            otpMsg.textContent = text;
            otpMsg.className = "login-message success";
          }
          if (pwdFields) pwdFields.hidden = false;
        } catch (err) {
          if (otpMsg) {
            otpMsg.textContent = err.message || "Could not send OTP.";
            otpMsg.className = "login-message error";
          }
        } finally {
          requestOtpBtn.disabled = false;
        }
      });
    }
    if (changePwdBtn) {
      changePwdBtn.addEventListener("click", async function () {
        const otpMsg = document.getElementById("otpMessage");
        const otp = (document.getElementById("profileOtpInput") || {}).value || "";
        const np = (document.getElementById("profileNewPassword") || {}).value || "";
        const cp = (document.getElementById("profileConfirmPassword") || {}).value || "";
        if (!otp.trim()) {
          if (otpMsg) {
            otpMsg.textContent = "Enter the OTP from your email.";
            otpMsg.className = "login-message error";
          }
          return;
        }
        if (np.length < 6) {
          if (otpMsg) {
            otpMsg.textContent = "New password must be at least 6 characters.";
            otpMsg.className = "login-message error";
          }
          return;
        }
        if (np !== cp) {
          if (otpMsg) {
            otpMsg.textContent = "New passwords do not match.";
            otpMsg.className = "login-message error";
          }
          return;
        }
        changePwdBtn.disabled = true;
        try {
          const res = await window.plagifyApi.changePasswordWithOtp({
            otp: otp.trim(),
            new_password: np,
            confirm_password: cp,
          });
          if (otpMsg) {
            otpMsg.textContent = res.message || "Password updated.";
            otpMsg.className = "login-message success";
          }
          ["profileOtpInput", "profileNewPassword", "profileConfirmPassword"].forEach(function (id) {
            const el = document.getElementById(id);
            if (el) el.value = "";
          });
          const pwdFields = document.getElementById("passwordChangeFields");
          if (pwdFields) pwdFields.hidden = true;
        } catch (err) {
          if (otpMsg) {
            otpMsg.textContent = err.message || "Could not change password.";
            otpMsg.className = "login-message error";
          }
        } finally {
          changePwdBtn.disabled = false;
        }
      });
    }
  }

  async function refreshProfileFromServer() {
    if (!window.plagifyApi || !window.plagifyApi.getToken || !window.plagifyApi.getToken()) {
      updateAuthUI(null);
      return;
    }
    try {
      const me = await window.plagifyApi.me();
      const profile = {
        email: me.email,
        name: me.name,
        picture: me.picture,
        auth_provider: me.auth_provider,
      };
      localStorage.setItem("plagifyUserProfile", JSON.stringify(profile));
      localStorage.setItem("plagifyLoggedIn", "true");
      localStorage.setItem("plagifyUser", me.email);
      updateAuthUI(profile);
    } catch {
      if (window.plagifyApi.clearToken) window.plagifyApi.clearToken();
      updateAuthUI(null);
    }
  }

  function onReady() {
    bindToggle();
    bindUserMenu();
    updateAuthUI();
    // Load api.js may be after theme.js — slight delay for me()
    setTimeout(refreshProfileFromServer, 50);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }

  window.plagifyTheme = { updateAuthUI, applyTheme };
})();
