/**
 * PLAGIFY Landing Page Script
 * Handles hero animations, counters, scroll effects, and interactions
 */

(function () {
  'use strict';

  // Initialize AOS
  AOS.init({ duration: 800, easing: 'ease-out-cubic', once: true, offset: 80 });

  // Preloader
  var preloader = document.getElementById('preloader');
  window.addEventListener('load', function () {
    setTimeout(function () { preloader.classList.add('hide'); }, 400);
  });
  setTimeout(function () { preloader.classList.add('hide'); }, 2500);

  // Mobile menu toggle
  const menuToggle = document.getElementById('menuToggle');
  const mainNav = document.getElementById('mainNav');
  if (menuToggle && mainNav) {
    menuToggle.addEventListener('click', () => {
      const isOpen = mainNav.classList.toggle('open');
      menuToggle.setAttribute('aria-expanded', isOpen);
    });
  }

  // Close mobile menu when clicking a link
  document.querySelectorAll('#mainNav .nav-link').forEach(function (link) {
    link.addEventListener('click', function () {
      mainNav.classList.remove('open');
      menuToggle.setAttribute('aria-expanded', 'false');
    });
  });

  // Header scroll state
  const header = document.getElementById('siteHeader');
  function onScroll() {
    if (window.scrollY > 40) header.classList.add('scrolled');
    else header.classList.remove('scrolled');
    updateScrollProgress();
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Hero mouse parallax
  var heroSection = document.querySelector('.hero');
  var heroGlobA = document.querySelector('.hero-glob.blob-a');
  var heroGlobB = document.querySelector('.hero-glob.blob-b');
  if (heroSection && window.matchMedia('(pointer:fine)').matches) {
    heroSection.addEventListener('mousemove', function (e) {
      var rect = heroSection.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;
      if (heroGlobA) heroGlobA.style.transform = 'translate(' + (x - rect.width/2) * 0.08 + 'px,' + (y - rect.height/2) * 0.08 + 'px)';
      if (heroGlobB) heroGlobB.style.transform = 'translate(' + (x - rect.width/2) * -0.05 + 'px,' + (y - rect.height/2) * -0.05 + 'px)';
    });
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        const headerHeight = header.offsetHeight;
        const targetPosition = target.getBoundingClientRect().top + window.scrollY - headerHeight;
        window.scrollTo({ top: targetPosition, behavior: 'smooth' });
      }
    });
  });

  // Scroll to top button with progress ring
  const scrollTop = document.getElementById('scrollTop');
  const progressRing = scrollTop?.querySelector('.progress-ring');
  if (scrollTop && progressRing) {
    const radius = 23;
    const circumference = 2 * Math.PI * radius;
    progressRing.style.strokeDasharray = circumference;
    progressRing.style.strokeDashoffset = circumference;

    function updateScrollProgress() {
      const scrollTopPos = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? scrollTopPos / docHeight : 0;
      progressRing.style.strokeDashoffset = circumference - progress * circumference;
      if (scrollTopPos > 300) scrollTop.classList.add('show');
      else scrollTop.classList.remove('show');
    }

    function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }
    scrollTop.addEventListener('click', scrollToTop);
    scrollTop.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); scrollToTop(); }
    });

    window.addEventListener('scroll', updateScrollProgress, { passive: true });
    updateScrollProgress();
  }

  // Toast notification system
  window.showToast = function (message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    const icons = {
      success: '<i class="bi bi-check-circle-fill"></i>',
      error: '<i class="bi bi-x-circle-fill"></i>',
      info: '<i class="bi bi-info-circle-fill"></i>',
      warning: '<i class="bi bi-exclamation-triangle-fill"></i>'
    };

    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <span class="toast-message">${message}</span>
      <button class="toast-close" aria-label="Dismiss">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
      toast.style.animation = 'toastIn 0.3s var(--ease) reverse';
      setTimeout(() => toast.remove(), 300);
    });

    container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        if (toast.parentNode) {
          toast.style.animation = 'toastIn 0.3s var(--ease) reverse';
          setTimeout(() => toast.remove(), 300);
        }
      }, duration);
    }
  };

  // Initialize auth UI on load
  if (window.plagifyTheme && window.plagifyTheme.updateAuthUI) {
    window.plagifyTheme.updateAuthUI();
  }
})();