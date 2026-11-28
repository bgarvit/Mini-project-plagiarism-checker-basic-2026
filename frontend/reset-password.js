/**
 * PLAGIFY Reset Password Page Script
 * Handles password reset with token validation
 */

(function () {
  'use strict';

  const form = document.getElementById('resetForm');
  const tokenInput = document.getElementById('resetToken');
  const newPasswordEl = document.getElementById('newPassword');
  const confirmPasswordEl = document.getElementById('confirmPassword');
  const submitBtn = document.getElementById('resetSubmitBtn');
  const btnText = submitBtn?.querySelector('.btn-text');
  const btnLoading = submitBtn?.querySelector('.btn-loading');
  const message = document.getElementById('resetMessage');
  const tokenError = document.getElementById('tokenError');
  const successState = document.getElementById('resetSuccessState');

  // Password strength elements
  const strengthFill = document.getElementById('strengthFill');
  const strengthFeedback = document.getElementById('strengthFeedback');
  const labelWeak = document.getElementById('labelWeak');
  const labelFair = document.getElementById('labelFair');
  const labelGood = document.getElementById('labelGood');
  const labelStrong = document.getElementById('labelStrong');

  // Match hint
  const matchHint = document.getElementById('matchHint');

  // Extract token from URL
  function getTokenFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('token');
  }

  // Initialize token
  const token = getTokenFromUrl();
  if (token) {
    tokenInput.value = token;
  } else {
    // No token in URL - show error
    form.hidden = true;
    tokenError.hidden = false;
  }

  // Password visibility toggles
  function wireShow(btnId, inputId) {
    const btn = document.getElementById(btnId);
    const input = document.getElementById(inputId);
    if (!btn || !input) return;
    
    const toggleIcon = btn.querySelector('i');
    const toggleText = btn.querySelector('.toggle-text');
    
    btn.addEventListener('click', function () {
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      
      if (toggleIcon) {
        toggleIcon.className = showing ? 'bi bi-eye' : 'bi bi-eye-slash';
      }
      if (toggleText) {
        toggleText.textContent = showing ? 'Show' : 'Hide';
      }
      btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
    });
  }
  wireShow('showNewPassword', 'newPassword');
  wireShow('showConfirmPassword', 'confirmPassword');

  // Password strength checker
  function checkPasswordStrength(password) {
    let score = 0;
    const feedback = [];

    if (password.length >= 8) score += 1;
    else feedback.push('At least 8 characters');

    if (password.length >= 12) score += 1;

    if (/[a-z]/.test(password)) score += 1;
    else feedback.push('Lowercase letter');

    if (/[A-Z]/.test(password)) score += 1;
    else feedback.push('Uppercase letter');

    if (/[0-9]/.test(password)) score += 1;
    else feedback.push('Number');

    if (/[^a-zA-Z0-9]/.test(password)) score += 1;
    else feedback.push('Special character');

    // Determine strength level
    let level = 0; // 0: weak, 1: fair, 2: good, 3: strong
    if (score <= 2) level = 0;
    else if (score === 3) level = 1;
    else if (score === 4) level = 2;
    else level = 3;

    return { score, level, feedback };
  }

  function updatePasswordStrength(password) {
    if (!strengthFill || !strengthFeedback) return;

    const { score, level, feedback } = checkPasswordStrength(password);

    // Update strength bar
    const widths = ['25%', '50%', '75%', '100%'];
    const colors = ['var(--clr-accent)', 'var(--clr-secondary)', '#0ea5e9', 'var(--clr-primary)'];
    const feedbackTexts = [
      'Add more characters, uppercase, numbers, or symbols',
      'Good start! Add uppercase, numbers, or symbols',
      'Strong password! Add a special character for maximum security',
      'Excellent! Very secure password'
    ];

    strengthFill.style.width = widths[level];
    strengthFill.style.background = colors[level];
    strengthFeedback.textContent = feedbackTexts[level];
    strengthFeedback.style.color = colors[level];

    // Update labels
    const allLabels = [labelWeak, labelFair, labelGood, labelStrong];
    allLabels.forEach((label, idx) => {
      if (label) {
        label.style.color = idx <= level ? colors[level] : 'var(--clr-text-light)';
        label.style.fontWeight = idx <= level ? '600' : '400';
      }
    });

    // Show/hide strength indicator
    const strengthContainer = document.getElementById('passwordStrength');
    if (strengthContainer) {
      if (password.length > 0) {
        strengthContainer.style.opacity = '1';
        strengthContainer.style.visibility = 'visible';
      } else {
        strengthContainer.style.opacity = '0';
        strengthContainer.style.visibility = 'hidden';
      }
    }
  }

  // Password input listener
  newPasswordEl?.addEventListener('input', function () {
    updatePasswordStrength(this.value);
    checkPasswordMatch();
  });

  // Confirm password match checker
  function checkPasswordMatch() {
    if (!matchHint || !confirmPasswordEl || !newPasswordEl) return;

    const password = newPasswordEl.value;
    const confirm = confirmPasswordEl.value;

    if (confirm.length === 0) {
      matchHint.textContent = '';
      matchHint.className = 'input-hint';
      confirmPasswordEl.style.borderColor = '';
      return;
    }

    if (password === confirm) {
      matchHint.textContent = '✓ Passwords match';
      matchHint.className = 'input-hint success';
      matchHint.style.color = 'var(--clr-primary)';
      confirmPasswordEl.style.borderColor = 'var(--clr-primary)';
    } else {
      matchHint.textContent = '✗ Passwords do not match';
      matchHint.className = 'input-hint error';
      matchHint.style.color = 'var(--clr-accent)';
      confirmPasswordEl.style.borderColor = 'var(--clr-accent)';
    }
  }

  confirmPasswordEl?.addEventListener('input', checkPasswordMatch);
  confirmPasswordEl?.addEventListener('blur', checkPasswordMatch);

  // Form submission
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const token = tokenInput.value.trim();
      const password = newPasswordEl.value;
      const confirm = confirmPasswordEl.value;

      // Clear previous messages
      message.textContent = '';
      message.className = 'login-message';

      // Validation
      if (!token) {
        showError('Invalid reset token.');
        return;
      }

      if (password.length < 8) {
        showError('Password must be at least 8 characters.');
        newPasswordEl?.focus();
        return;
      }

      const { level } = checkPasswordStrength(password);
      if (level === 0) {
        showError('Please choose a stronger password.');
        newPasswordEl?.focus();
        return;
      }

      if (password !== confirm) {
        showError('Passwords do not match.');
        confirmPasswordEl?.focus();
        return;
      }

      // Disable submit button
      setLoadingState(true);

      try {
        const data = await window.plagifyApi.resetPassword(token, password);
        
        // Save session and redirect
        window.plagifyApi.saveSession(data);
        form.hidden = true;
        successState.hidden = false;
        
        showToast('Password reset successful! Redirecting…', 'success');
        
        setTimeout(() => {
          window.location.href = 'index.html';
        }, 1500);
      } catch (error) {
        // Check if it's a token error
        if (error.message && (error.message.includes('token') || error.message.includes('Token'))) {
          form.hidden = true;
          tokenError.hidden = false;
        } else {
          showError(error.message || 'Password reset failed. Please try again.');
        }
        setLoadingState(false);
      }
    });
  }

  function setLoadingState(loading) {
    if (!submitBtn) return;
    
    submitBtn.disabled = loading;
    if (btnText) btnText.hidden = loading;
    if (btnLoading) btnLoading.hidden = !loading;
  }

  function showError(msg) {
    message.textContent = msg;
    message.className = 'login-message error';
    shakeForm();
  }

  function shakeForm() {
    const card = document.querySelector('.auth-card');
    if (card) {
      card.style.animation = 'none';
      card.offsetHeight; // Trigger reflow
      card.style.animation = 'shake 0.4s ease';
    }
  }

  // Initialize AOS
  AOS.init({ duration: 600, easing: 'ease-out-cubic', once: true, offset: 50 });

  // Initialize auth UI
  if (window.plagifyTheme && window.plagifyTheme.updateAuthUI) {
    window.plagifyTheme.updateAuthUI();
  }
})();