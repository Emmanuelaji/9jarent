// ============================================
// 9jaRent.com.ng - App JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initMobileSidebar();
    initConversationSelection();
    initChatComposer();
    initSearchFilter();
    initFavouriteToggle();
    initNotificationDropdown();
    initTabNavigation();
    initFormValidation();
    initPasswordStrength();
    initDateRangePicker();
    initLgaCascade();
    initPropertyGallery();
});

// ============================================
// CSRF helper (for fetch() calls - Django needs
// the X-CSRFToken header on same-origin POSTs)
// ============================================
function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

// ============================================
// Mobile Sidebar
// ============================================
function initMobileSidebar() {
    const menuBtn = document.querySelector('.mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (menuBtn && sidebar) {
        menuBtn.addEventListener('click', function() {
            sidebar.classList.toggle('show');
            if (overlay) overlay.classList.toggle('show');
        });
        
        if (overlay) {
            overlay.addEventListener('click', function() {
                sidebar.classList.remove('show');
                overlay.classList.remove('show');
            });
        }
    }
    
    // Close sidebar on window resize to desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 1200) {
            if (sidebar) sidebar.classList.remove('show');
            if (overlay) overlay.classList.remove('show');
        }
    });
}

// ============================================
// Conversation Selection
// ============================================
function initConversationSelection() {
    const conversationItems = document.querySelectorAll('.conversation-item');
    
    conversationItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remove active from all
            conversationItems.forEach(i => i.classList.remove('active'));
            // Add active to clicked
            this.classList.add('active');
            
            // Remove badge if exists
            const badge = this.querySelector('.conversation-item-badge');
            if (badge) badge.remove();
            
            // On mobile, scroll to chat
            if (window.innerWidth < 768) {
                const chatWindow = document.querySelector('.chat-window');
                if (chatWindow) {
                    chatWindow.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });
}

// ============================================
// Chat Composer
// ============================================
// The actual message send is a REAL Django form POST (see
// templates/messaging/inbox.html) - the server persists the message and
// re-renders the thread. This JS only enhances the UX: it lets the
// textarea submit on Enter (Shift+Enter still inserts a newline), since
// browsers don't submit a form on Enter inside a <textarea> by default.
// There is no client-side faking of messages here.
function initChatComposer() {
    const form = document.querySelector('.chat-composer');
    const textarea = document.querySelector('.chat-composer-input textarea');

    if (form && textarea) {
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (textarea.value.trim()) {
                    form.requestSubmit();
                }
            }
        });
    }
}

// ============================================
// Search Filter
// ============================================
function initSearchFilter() {
    const searchInputs = document.querySelectorAll('[data-search]');
    
    searchInputs.forEach(input => {
        const target = input.getAttribute('data-search');
        const items = document.querySelectorAll(target);
        
        input.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(query)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

// ============================================
// Favourite Toggle
// ============================================
// Real POST to /favourites/toggle/<id>/ via fetch() with the CSRF header
// Django requires - this actually persists the change (see
// favourites/views.py::toggle_favourite), it doesn't just flip a CSS class.
// Falls back to a normal full-page form submit if fetch fails for any reason.
function initFavouriteToggle() {
    document.querySelectorAll('form.js-fav-toggle').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const button = form.querySelector('button[type="submit"]');
            if (button) button.disabled = true;

            fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: new FormData(form),
            })
                .then(response => {
                    if (!response.ok) throw new Error('Request failed');
                    return response.json();
                })
                .then(data => {
                    applyFavouriteResult(form, data.favourited);
                })
                .catch(() => {
                    // Network/JS error - degrade to a normal form submit so the
                    // action still works (full page reload, server-rendered state).
                    form.submit();
                })
                .finally(() => {
                    if (button) button.disabled = false;
                });
        });
    });
}

function applyFavouriteResult(form, isFavourited) {
    const icon = form.querySelector('i.bi-heart, i.bi-heart-fill');
    if (icon) {
        icon.classList.toggle('bi-heart-fill', isFavourited);
        icon.classList.toggle('bi-heart', !isFavourited);
    }

    if (form.dataset.textMode === 'true') {
        const label = form.querySelector('.js-fav-label');
        if (label) label.textContent = isFavourited ? 'Saved to Favourites' : 'Save to Favourites';
        if (icon) icon.style.color = isFavourited ? 'var(--brand-orange)' : '';
    }

    if (!isFavourited && form.dataset.removeCardOnUnfav === 'true') {
        const card = form.closest('.fav-card');
        const column = card ? (card.closest('[class*="col-"]') || card) : form;
        column.style.transition = 'opacity 0.2s ease';
        column.style.opacity = '0';
        setTimeout(() => column.remove(), 200);
    }
}

// ============================================
// Notification Dropdown
// ============================================
function initNotificationDropdown() {
    const notifyBtn = document.querySelector('.top-bar-notify');
    const dropdown = document.querySelector('.notification-dropdown');
    
    if (notifyBtn && dropdown) {
        notifyBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });
        
        document.addEventListener('click', function() {
            dropdown.classList.remove('show');
        });
        
        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
}

// ============================================
// Tab Navigation
// ============================================
function initTabNavigation() {
    const tabGroups = document.querySelectorAll('[data-tabs]');
    
    tabGroups.forEach(group => {
        const tabs = group.querySelectorAll('[data-tab]');
        const panels = group.querySelectorAll('[data-panel]');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const target = this.getAttribute('data-tab');
                
                tabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                panels.forEach(p => {
                    if (p.getAttribute('data-panel') === target) {
                        p.classList.remove('d-none');
                    } else {
                        p.classList.add('d-none');
                    }
                });
            });
        });
    });
}

// ============================================
// Form Validation
// ============================================
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
        
        form.querySelectorAll('input, textarea, select').forEach(field => {
            field.addEventListener('input', function() {
                if (this.value.trim()) {
                    this.classList.remove('is-invalid');
                }
            });
        });
    });
}

// ============================================
// Password Strength
// ============================================
function initPasswordStrength() {
    const passwordInput = document.querySelector('input[data-password-strength]');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const value = this.value;
            const bars = document.querySelectorAll('.password-strength-bar');
            const text = document.querySelector('.password-strength-text');
            
            let strength = 0;
            if (value.length >= 8) strength++;
            if (/[A-Z]/.test(value)) strength++;
            if (/[0-9]/.test(value)) strength++;
            if (/[^A-Za-z0-9]/.test(value)) strength++;
            
            bars.forEach((bar, index) => {
                if (index < strength) {
                    bar.classList.add('active');
                } else {
                    bar.classList.remove('active');
                }
            });
            
            if (text) {
                const labels = ['Weak', 'Fair', 'Good', 'Strong'];
                text.textContent = strength > 0 ? `Password strength: ${labels[strength - 1]}` : '';
                text.className = 'password-strength-text' + (strength >= 3 ? ' strong' : '');
            }
        });
    }
}

// ============================================
// Date Range Picker
// ============================================
function initDateRangePicker() {
    const datePickers = document.querySelectorAll('input[type="date"]');
    
    datePickers.forEach(picker => {
        picker.addEventListener('change', function() {
            // Custom date validation can go here
        });
    });
}

// ============================================
// Property Thumbnail Gallery
// ============================================
function initPropertyGallery() {
    const mainImage = document.querySelector('.property-main-image');
    const thumbnails = document.querySelectorAll('.property-thumbnail');
    
    thumbnails.forEach(thumb => {
        thumb.addEventListener('click', function() {
            if (mainImage) {
                mainImage.src = this.src;
            }
            thumbnails.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// ============================================
// Smooth Scroll
// ============================================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// ============================================
// Toast Notifications
// ============================================
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'warning'} position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// ============================================
// Cascading State -> LGA dropdown (property forms)
// ============================================
function initLgaCascade() {
    const stateSelect = document.getElementById('id_state');
    const lgaSelect = document.getElementById('id_lga');
    if (!stateSelect || !lgaSelect) return;

    const ajaxUrl = lgaSelect.dataset.ajaxUrl;
    if (!ajaxUrl) return;

    function loadLgas(stateId, selectedLgaId) {
        lgaSelect.disabled = true;
        if (!stateId) {
            lgaSelect.innerHTML = '<option value="">Select a state first</option>';
            lgaSelect.disabled = false;
            return;
        }
        lgaSelect.innerHTML = '<option value="">Loading...</option>';
        fetch(`${ajaxUrl}?state=${encodeURIComponent(stateId)}`)
            .then(response => response.json())
            .then(data => {
                lgaSelect.innerHTML = '<option value="">Select LGA</option>';
                data.lgas.forEach(lga => {
                    const opt = document.createElement('option');
                    opt.value = lga.id;
                    opt.textContent = lga.name;
                    if (selectedLgaId && String(lga.id) === String(selectedLgaId)) {
                        opt.selected = true;
                    }
                    lgaSelect.appendChild(opt);
                });
                lgaSelect.disabled = false;
            })
            .catch(() => {
                lgaSelect.innerHTML = '<option value="">Could not load LGAs - try reselecting the state</option>';
                lgaSelect.disabled = false;
            });
    }

    stateSelect.addEventListener('change', function () {
        loadLgas(this.value, null);
    });

    // On page load (e.g. editing an existing property), preserve whatever
    // LGA was already selected server-side instead of wiping it.
    const initialLgaId = lgaSelect.dataset.initialValue;
    if (stateSelect.value) {
        loadLgas(stateSelect.value, initialLgaId);
    }
}