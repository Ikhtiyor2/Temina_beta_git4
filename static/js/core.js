// Core JavaScript for TeminaFit Premium

class TeminaFitApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initAnimations();
        this.loadUserPreferences();
    }

    setupEventListeners() {
        // Navigation
        this.setupNavigation();
        
        // Theme handling
        this.setupTheme();
        
        // Modal handling
        this.setupModals();
    }

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                navItems.forEach(nav => nav.classList.remove('active'));
                e.currentTarget.classList.add('active');
            });
        });

        // Mobile menu toggle
        const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', this.toggleMobileMenu);
        }
    }

    setupTheme() {
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', this.toggleTheme);
        }

        // Load saved theme (новый ключ + старый для миграции)
        const savedTheme =
            localStorage.getItem('temina-fit-theme') ?? localStorage.getItem('teminafit-theme');
        if (savedTheme) {
            document.body.setAttribute('data-theme', savedTheme);
        }
    }

    toggleTheme() {
        const currentTheme = document.body.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('temina-fit-theme', newTheme);
        localStorage.removeItem('teminafit-theme');
    }

    setupModals() {
        // Close modals on backdrop click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-backdrop')) {
                this.closeModal(e.target);
            }
        });

        // Close modals with escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    closeModal(modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    closeAllModals() {
        const modals = document.querySelectorAll('.modal-backdrop.active');
        modals.forEach(modal => this.closeModal(modal));
    }

    initAnimations() {
        // Intersection Observer for scroll animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, observerOptions);

        // Observe elements with animation classes
        document.querySelectorAll('.premium-card, .glass-panel').forEach(el => {
            observer.observe(el);
        });
    }

    loadUserPreferences() {
        // Load user settings from localStorage
        const prefRaw =
            localStorage.getItem('temina-fit-preferences') ??
            localStorage.getItem('teminafit-preferences');
        const preferences = JSON.parse(prefRaw || '{}') || {};
        this.applyPreferences(preferences);
    }

    applyPreferences(preferences) {
        // Apply volume settings
        if (preferences.volume !== undefined) {
            this.setVolume(preferences.volume);
        }

        // Apply notification settings
        if (preferences.notifications !== undefined) {
            this.setNotifications(preferences.notifications);
        }
    }

    // Utility functions
    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `premium-notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${this.getNotificationIcon(type)}</span>
                <span class="notification-message">${message}</span>
            </div>
        `;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);

        // Remove after delay
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    getNotificationIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.teminaFitApp = new TeminaFitApp();
});

// Utility functions for API calls
class ApiClient {
    static async get(url) {
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('API GET Error:', error);
            throw error;
        }
    }

    static async post(url, data) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('API POST Error:', error);
            throw error;
        }
    }

    static getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}