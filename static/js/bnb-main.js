/* ==========================================================================
   BHARAT NIDHI BANK (BNB) - MASTER JAVASCRIPT
   Clean, vanilla, standard-compliant interactions
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
  // Mobile Sidebar Toggle
  const sidebarToggle = document.getElementById('bnbSidebarToggle');
  const sidebar = document.getElementById('bnbSidebar');
  const sidebarBackdrop = document.getElementById('bnbSidebarBackdrop');

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
      if (sidebarBackdrop) {
        sidebarBackdrop.classList.toggle('d-none');
      }
    });
  }

  if (sidebarBackdrop && sidebar) {
    sidebarBackdrop.addEventListener('click', function () {
      sidebar.classList.remove('show');
      sidebarBackdrop.classList.add('d-none');
    });
  }

  // Password Visibility Toggle
  const togglePasswordBtns = document.querySelectorAll('.bnb-toggle-password');
  togglePasswordBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      const targetSelector = this.getAttribute('data-target');
      const input = document.querySelector(targetSelector);
      if (input) {
        const isPassword = input.getAttribute('type') === 'password';
        input.setAttribute('type', isPassword ? 'text' : 'password');
        const icon = this.querySelector('i');
        if (icon) {
          icon.classList.toggle('bi-eye');
          icon.classList.toggle('bi-eye-slash');
        }
      }
    });
  });

  // OTP 6-Box Auto-Advancement
  const otpInputs = document.querySelectorAll('.bnb-otp-digit');
  const fullOtpInput = document.querySelector('#id_otp');

  if (otpInputs.length === 6) {
    otpInputs.forEach((input, idx) => {
      input.addEventListener('input', function (e) {
        const val = this.value.replace(/[^0-9]/g, '');
        this.value = val ? val[0] : '';
        if (this.value && idx < 5) {
          otpInputs[idx + 1].focus();
        }
        syncFullOtp();
      });

      input.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && !this.value && idx > 0) {
          otpInputs[idx - 1].focus();
        }
      });

      input.addEventListener('paste', function (e) {
        e.preventDefault();
        const pasteData = (e.clipboardData || window.clipboardData).getData('text').trim();
        const digits = pasteData.replace(/[^0-9]/g, '').slice(0, 6);
        for (let i = 0; i < digits.length; i++) {
          if (otpInputs[i]) {
            otpInputs[i].value = digits[i];
          }
        }
        syncFullOtp();
        if (digits.length >= 6) {
          otpInputs[5].focus();
        } else if (otpInputs[digits.length]) {
          otpInputs[digits.length].focus();
        }
      });
    });

    function syncFullOtp() {
      if (fullOtpInput) {
        let code = '';
        otpInputs.forEach(i => code += i.value);
        fullOtpInput.value = code;
      }
    }
  }

  // Auto-dismiss Django success alerts after 6 seconds
  const autoAlerts = document.querySelectorAll('.alert-auto-dismiss');
  autoAlerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500);
    }, 6000);
  });
});
