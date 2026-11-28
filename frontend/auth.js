/**
 * PLAGIFY Login Page Script
 * Handles authentication form submission and UI interactions
 */

(function () {
  'use strict';

  const loginForm = document.getElementById('loginForm');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const showPasswordBtn = document.getElementById('showPassword');
  const forgotPasswordLink = document.getElementById('forgotPassword');
  const loginMessage = document.getElementById('loginMessage');
  const submitBtn = loginForm?.querySelector('button[type="submit"]');
  const btnText = submitBtn?.querySelector('.btn-text');
  const btnLoading = submitBtn?.querySelector('.btn-loading');

  // Password visibility toggle
  if (showPasswordBtn && passwordInput) {
    const toggleIcon = showPasswordBtn.querySelector('i');
    const toggleText = showPasswordBtn.querySelector('.toggle-text');
    
    showPasswordBtn.addEventListener('click', () => {
      const isVisible = passwordInput.type === 'text';
      passwordInput.type = isVisible ? 'password' : 'text';
      
      if (toggleIcon) {
        toggleIcon.className = isVisible ? 'bi bi-eye' : 'bi bi-eye-slash';
      }
      if (toggleText) {
        toggleText.textContent = isVisible ? 'Show' : 'Hide';
      }
      showPasswordBtn.setAttribute('aria-label', isVisible ? 'Show password' : 'Hide password');
    });
  }

  // Form submission
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = emailInput.value.trim();
      const password = passwordInput.value.trim();

      // Clear previous messages
      loginMessage.textContent = '';
      loginMessage.className = 'login-message';

      // Validation
      if (!email || !password) {
        showError('Please enter your email and password.');
        return;
      }

      if (!isValidEmail(email)) {
        showError('Please enter a valid email address.');
        return;
      }

      if (password.length < 6) {
        showError('Password must contain at least 6 characters.');
        return;
      }

      // Disable submit button with loading state
      setLoadingState(true);

      try {
        const data = await window.plagifyApi.login(email, password);
        window.plagifyApi.saveSession(data);

        showSuccess('Login successful. Redirecting…');

        setTimeout(() => {
          window.location.href = 'index.html';
        }, 800);
      } catch (error) {
        showError(error.message || 'Login failed. Please try again.');
        setLoadingState(false);
      }
    });
  }

  function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }

  function setLoadingState(loading) {
    if (!submitBtn) return;
    
    submitBtn.disabled = loading;
    if (btnText) btnText.hidden = loading;
    if (btnLoading) btnLoading.hidden = !loading;
    
    if (!loading) {
      submitBtn.innerHTML = '<span class="btn-text">Sign In</span><span class="btn-loading" hidden><span class="spinner spinner-sm"></span> Signing in…</span><i class="bi bi-arrow-right"></i>';
    }
  }

  function showError(message) {
    loginMessage.textContent = message;
    loginMessage.className = 'login-message error';
    shakeForm();
  }

  function showSuccess(message) {
    loginMessage.textContent = message;
    loginMessage.className = 'login-message success';
  }

  function shakeForm() {
    const card = document.querySelector('.auth-card');
    if (card) {
      card.style.animation = 'none';
      card.offsetHeight; // Trigger reflow
      card.style.animation = 'shake 0.4s ease';
    }
  }


  // ---------- Google Sign-In ----------
  const googleBtn = document.getElementById('googleSignInBtn');
  let googleTokenClient = null;

  async function finishGoogleLogin(payload) {
    try {
      if (googleBtn) googleBtn.disabled = true;
      const data = await window.plagifyApi.googleLogin(payload);
      window.plagifyApi.saveSession(data);
      showSuccess('Google sign-in successful. Redirecting…');
      setTimeout(function () {
        window.location.href = 'index.html';
      }, 800);
    } catch (err) {
      showError(err.message || 'Google sign-in failed.');
      if (googleBtn) googleBtn.disabled = false;
    }
  }

  function initGoogleSignIn(clientId) {
    if (!clientId) {
      if (googleBtn) {
        googleBtn.onclick = function () {
          showError('Google sign-in is not configured on the server.');
        };
      }
      return;
    }

    function setupGis() {
      if (!window.google || !window.google.accounts || !window.google.accounts.oauth2) {
        return false;
      }

      googleTokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope: 'openid email profile',
        callback: function (tokenResponse) {
          if (tokenResponse && tokenResponse.error) {
            showError(tokenResponse.error_description || tokenResponse.error || 'Google login cancelled.');
            if (googleBtn) googleBtn.disabled = false;
            return;
          }
          if (tokenResponse && tokenResponse.access_token) {
            finishGoogleLogin({ access_token: tokenResponse.access_token });
          } else {
            showError('Google did not return an access token.');
            if (googleBtn) googleBtn.disabled = false;
          }
        },
      });

      if (googleBtn) {
        googleBtn.onclick = function () {
          if (!googleTokenClient) {
            showError('Google Sign-In is still loading. Try again.');
            return;
          }
          googleTokenClient.requestAccessToken({ prompt: 'select_account' });
        };
      }
      return true;
    }

    if (!setupGis()) {
      var tries = 0;
      var timer = setInterval(function () {
        tries += 1;
        if (setupGis() || tries > 50) clearInterval(timer);
      }, 100);
    }
  }

  if (window.plagifyApi && window.plagifyApi.authConfig) {
    window.plagifyApi.authConfig()
      .then(function (cfg) {
        initGoogleSignIn(cfg && cfg.google_client_id ? cfg.google_client_id : null);
      })
      .catch(function () {
        initGoogleSignIn(null);
        showError('Cannot reach API. Open http://127.0.0.1:8700/login.html via the server.');
      });
  } else if (googleBtn) {
    googleBtn.onclick = function () {
      showError('API not loaded. Refresh the page.');
    };
  }

// Initialize AOS
  AOS.init({ duration: 600, easing: 'ease-out-cubic', once: true, offset: 50 });

  // Initialize auth UI
  if (window.plagifyTheme && window.plagifyTheme.updateAuthUI) {
    window.plagifyTheme.updateAuthUI();
  }
})();