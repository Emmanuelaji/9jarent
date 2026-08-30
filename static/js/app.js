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
});

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
function initChatComposer() {
    const input = document.querySelector('.chat-composer-input input');
    const sendBtn = document.querySelector('.chat-composer-send');
    const messagesContainer = document.querySelector('.chat-messages');
    
    if (input && sendBtn && messagesContainer) {
        sendBtn.addEventListener('click', function() {
            sendMessage();
        });
        
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        function sendMessage() {
            const text = input.value.trim();
            if (!text) return;
            
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            
            const messageHTML = `
                <div class="message-bubble message-outgoing">
                    <div>${escapeHtml(text)}</div>
                    <div class="message-time">
                        ${timeStr}
                        <i class="bi bi-check2-all message-read"></i>
                    </div>
                </div>
            `;
            
            messagesContainer.insertAdjacentHTML('beforeend', messageHTML);
            input.value = '';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // Simulate reply after 2 seconds
            setTimeout(function() {
                const replyHTML = `
                    <div class="message-bubble message-incoming">
                        <div>Thank you for your message. I'll get back to you shortly.</div>
                        <div class="message-time">${timeStr}</div>
                    </div>
                `;
                messagesContainer.insertAdjacentHTML('beforeend', replyHTML);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }, 2000);
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
function initFavouriteToggle() {
    const favButtons = document.querySelectorAll('.fav-toggle, .fav-card-heart');
    
    favButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const icon = this.querySelector('i') || this;
            if (icon.classList.contains('bi-heart-fill')) {
                icon.classList.remove('bi-heart-fill');
                icon.classList.add('bi-heart');
            } else {
                icon.classList.remove('bi-heart');
                icon.classList.add('bi-heart-fill');
            }
        });
    });
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
// Pagination
// ============================================
function initPagination() {
    const paginationItems = document.querySelectorAll('.pagination-custom .page-link');
    
    paginationItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            const parent = this.closest('.page-item');
            if (parent.classList.contains('disabled') || parent.classList.contains('active')) return;
            
            document.querySelectorAll('.pagination-custom .page-item').forEach(p => p.classList.remove('active'));
            parent.classList.add('active');
        });
    });
}

// ============================================
// Account Type Selection
// ============================================
function selectAccountType(type) {
    const cards = document.querySelectorAll('.account-type-card');
    cards.forEach(card => {
        card.style.borderColor = '';
        card.style.boxShadow = '';
    });
    
    const selectedCard = document.querySelector(`.account-type-card[data-type="${type}"]`);
    if (selectedCard) {
        selectedCard.style.borderColor = 'var(--brand-green)';
        selectedCard.style.boxShadow = '0 4px 16px rgba(0,0,0,0.06)';
    }
}
