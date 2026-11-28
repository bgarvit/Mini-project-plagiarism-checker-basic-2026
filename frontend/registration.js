/**
 * PLAGIFY Registration Page Script
 * Handles account creation form with password strength indicator
 */

(function () {
  'use strict';

  const form = document.getElementById('registerForm');
  if (!form) return;

  const nameEl = document.getElementById('regName');
  const emailEl = document.getElementById('regEmail');
  const phoneEl = document.getElementById('regPhone');
  const institutionEl = document.getElementById('regInstitution');
  const roleEl = document.getElementById('regRole');
  const passwordEl = document.getElementById('regPassword');
  const confirmEl = document.getElementById('regConfirm');
  const termsEl = document.getElementById('regTerms');
  const message = document.getElementById('regMessage');
  const submitBtn = document.getElementById('regSubmitBtn');
  const btnText = submitBtn?.querySelector('.btn-text');
  const btnLoading = submitBtn?.querySelector('.btn-loading');

  // Password strength elements
  const strengthFill = document.getElementById('strengthFill');
  const strengthFeedback = document.getElementById('strengthFeedback');
  const labelWeak = document.getElementById('labelWeak');
  const labelFair = document.getElementById('labelFair');
  const labelGood = document.getElementById('labelGood');
  const labelStrong = document.getElementById('labelStrong');

  // Match hint
  const matchHint = document.getElementById('matchHint');

  // Modal elements
  const termsModal = document.getElementById('termsModal');
  const privacyModal = document.getElementById('privacyModal');
  const termsLink = document.getElementById('termsLink');
  const privacyLink = document.getElementById('privacyLink');
  const termsAcceptBtn = document.getElementById('termsAcceptBtn');
  const termsDeclineBtn = document.getElementById('termsDeclineBtn');
  const privacyAcceptBtn = document.getElementById('privacyAcceptBtn');
  const privacyDeclineBtn = document.getElementById('privacyDeclineBtn');
  const termsModalClose = document.getElementById('termsModalClose');
  const privacyModalClose = document.getElementById('privacyModalClose');

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
  wireShow('regShowPassword', 'regPassword');
  wireShow('regShowConfirm', 'regConfirm');

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
  passwordEl?.addEventListener('input', function () {
    updatePasswordStrength(this.value);
    checkPasswordMatch();
  });

  // Confirm password match checker
  function checkPasswordMatch() {
    if (!matchHint || !confirmEl || !passwordEl) return;

    const password = passwordEl.value;
    const confirm = confirmEl.value;

    if (confirm.length === 0) {
      matchHint.textContent = '';
      matchHint.className = 'input-hint';
      confirmEl.style.borderColor = '';
      return;
    }

    if (password === confirm) {
      matchHint.textContent = '✓ Passwords match';
      matchHint.className = 'input-hint success';
      matchHint.style.color = 'var(--clr-primary)';
      confirmEl.style.borderColor = 'var(--clr-primary)';
    } else {
      matchHint.textContent = '✗ Passwords do not match';
      matchHint.className = 'input-hint error';
      matchHint.style.color = 'var(--clr-accent)';
      confirmEl.style.borderColor = 'var(--clr-accent)';
    }
  }

  confirmEl?.addEventListener('input', checkPasswordMatch);
  confirmEl?.addEventListener('blur', checkPasswordMatch);

  // Modal handlers
  function openModal(modal) {
    if (modal) {
      modal.hidden = false;
      document.body.style.overflow = 'hidden';
      // Focus first focusable element
      const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusable) focusable.focus();
    }
  }

  function closeModal(modal) {
    if (modal) {
      modal.hidden = true;
      document.body.style.overflow = '';
    }
  }

  // Terms link
  termsLink?.addEventListener('click', (e) => {
    e.preventDefault();
    openModal(termsModal);
  });

  // Privacy link
  privacyLink?.addEventListener('click', (e) => {
    e.preventDefault();
    openModal(privacyModal);
  });

  // Close modals
  [termsModalClose, privacyModalClose].forEach(btn => {
    btn?.addEventListener('click', () => closeModal(btn.closest('.modal-overlay')));
  });

  // Accept/Decline buttons
  termsAcceptBtn?.addEventListener('click', () => {
    if (termsEl) termsEl.checked = true;
    document.getElementById('termsGroup')?.classList.remove('has-error');
    closeModal(termsModal);
  });
  termsDeclineBtn?.addEventListener('click', () => {
    closeModal(termsModal);
    termsEl.checked = false;
    termsEl.focus();
  });
  
  privacyAcceptBtn?.addEventListener('click', () => {
    if (termsEl) termsEl.checked = true;
    document.getElementById('termsGroup')?.classList.remove('has-error');
    closeModal(privacyModal);
  });
  privacyDeclineBtn?.addEventListener('click', () => {
    closeModal(privacyModal);
    termsEl.checked = false;
    termsEl.focus();
  });

  // Close on overlay click
  [termsModal, privacyModal].forEach(modal => {
    modal?.addEventListener('click', (e) => {
      if (e.target === modal) closeModal(modal);
    });
  });

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (!termsModal?.hidden) closeModal(termsModal);
      if (!privacyModal?.hidden) closeModal(privacyModal);
    }
  });

  // Form submission
  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const name = (nameEl?.value || '').trim();
    const email = (emailEl?.value || '').trim();
    const phone = (phoneEl?.value || '').trim();
    const institution = (institutionEl?.value || '').trim();
    const role = (roleEl?.value || '').trim();
    const password = passwordEl?.value || '';
    const confirm = confirmEl?.value || '';
    const terms = termsEl?.checked;

    clearMessage();
    document.getElementById('termsGroup')?.classList.remove('has-error');

    // Validation
    if (name.length < 2) {
      showError('Full name must be at least 2 characters.');
      nameEl?.focus();
      return;
    }

    if (!isValidEmail(email)) {
      showError('Please enter a valid email address.');
      emailEl?.focus();
      return;
    }

    if (phone && !/^[0-9+\-\s]{7,15}$/.test(phone)) {
      showError('Please enter a valid phone number (digits only, 7–15 characters).');
      phoneEl?.focus();
      return;
    }

    if (!role) {
      showError('Please select your role (student, teacher, etc.).');
      roleEl?.focus();
      return;
    }

    if (password.length < 8) {
      showError('Password must be at least 8 characters.');
      passwordEl?.focus();
      return;
    }

    const { level } = checkPasswordStrength(password);
    if (level === 0) {
      showError('Please choose a stronger password.');
      passwordEl?.focus();
      return;
    }

    if (password !== confirm) {
      showError('Passwords do not match.');
      confirmEl?.focus();
      return;
    }

    if (!terms) {
      showError('You must accept the Terms of Service and Privacy Policy.');
      document.getElementById('termsGroup')?.classList.add('has-error');
      termsEl?.focus();
      return;
    }

    // Disable submit button
    setLoadingState(true);

    try {
      const data = await window.plagifyApi.register({
        email,
        password,
        name,
        phone: phone || null,
        institution: institution || null,
        role,
        picture: null,
        accepted_terms: true,
      });

      window.plagifyApi.saveSession(data);
      showSuccess('Account created. Redirecting…');

      setTimeout(function () {
        window.location.href = 'index.html';
      }, 800);
    } catch (error) {
      showError(error.message || 'Registration failed.');
      setLoadingState(false);
    }
  });

  function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
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

  function showSuccess(msg) {
    message.textContent = msg;
    message.className = 'login-message success';
  }

  function clearMessage() {
    message.textContent = '';
    message.className = 'login-message';
  }

  function shakeForm() {
    const card = document.querySelector('.auth-card');
    if (card) {
      card.style.animation = 'none';
      card.offsetHeight;
      card.style.animation = 'shake 0.4s ease';
    }
  }

  // Initialize AOS
  AOS.init({ duration: 600, easing: 'ease-out-cubic', once: true, offset: 50 });
})();