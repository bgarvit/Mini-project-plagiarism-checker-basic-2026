/**
 * PLAGIFY Forgot Password Page Script
 * Handles password reset request flow
 */

(function () {
  'use strict';

  const form = document.getElementById('forgotForm');
  const emailInput = document.getElementById('resetEmail');
  const submitBtn = document.getElementById('forgotSubmitBtn');
  const message = document.getElementById('forgotMessage');
  const successState = document.getElementById('resetSuccessState');
  const sentEmailEl = document.getElementById('sentEmail');
  const resendBtn = document.getElementById('resendLinkBtn');
  const contactSupport = document.getElementById('contactSupport');

  let resendCooldown = 0;
  let resendTimer = null;

  // Form submission
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = emailInput.value.trim();

      // Clear previous messages
      message.textContent = '';
      message.className = 'login-message';

      // Validation
      if (!email) {
        showError('Please enter your email address.');
        return;
      }

      if (!isValidEmail(email)) {
        showError('Please enter a valid email address.');
        return;
      }

      // Disable submit button
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner spinner-sm"></span> Sending…';

      try {
        // Call backend forgot password endpoint
        await window.plagifyApi.forgotPassword(email);
        
        // Show success state
        form.hidden = true;
        successState.hidden = false;
        sentEmailEl.textContent = email;
        startResendCooldown();
        
        showToast('Password reset link sent! Check your email.', 'success');
      } catch (error) {
        showError(error.message || 'Failed to send reset link. Please try again.');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span class="btn-text">Send Reset Link</span><i class="bi bi-send"></i>';
      }
    });
  }

  // Resend link
  if (resendBtn) {
    resendBtn.addEventListener('click', async () => {
      if (resendCooldown > 0) return;
      
      const email = emailInput.value.trim();
      if (!email) return;

      resendBtn.disabled = true;
      resendBtn.innerHTML = '<span class="spinner spinner-sm"></span> Sending…';

      try {
        await window.plagifyApi.forgotPassword(email);
        showToast('Reset link sent again!', 'success');
        startResendCooldown();
      } catch (error) {
        showToast(error.message || 'Failed to resend. Please try again.', 'error');
        resendBtn.disabled = false;
        resendBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Resend Email';
      }
    });
  }

  // Contact support
  if (contactSupport) {
    contactSupport.addEventListener('click', (e) => {
      e.preventDefault();
      showToast('Please contact support at plagify4u@gmail.com', 'info');
    });
  }

  function isValidEmail(email) {
    // Basic email validation
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }

  function showError(msg) {
    message.textContent = msg;
    message.className = 'login-message error';
    shakeForm();
  }

  function startResendCooldown() {
    resendCooldown = 60; // 60 seconds
    resendBtn.disabled = true;
    
    resendTimer = setInterval(() => {
      resendCooldown--;
      if (resendCooldown > 0) {
        resendBtn.innerHTML = `<i class="bi bi-arrow-clockwise"></i> Resend in ${resendCooldown}s`;
      } else {
        clearInterval(resendTimer);
        resendBtn.disabled = false;
        resendBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Resend Email';
      }
    }, 1000);
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