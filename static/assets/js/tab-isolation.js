// static/js/tab-isolation.js
(function() {
    'use strict';

    // Generate unique tab ID
    const TAB_ID = 'tab_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    const ACTIVE_TAB_KEY = 'edu_active_tab';
    const SESSION_KEY = 'edu_session_data';

    console.log('🔹 Tab ID:', TAB_ID);

    // Store tab ID
    sessionStorage.setItem(ACTIVE_TAB_KEY, TAB_ID);

    // Check if this tab is active
    function isThisTabActive() {
        const activeTab = localStorage.getItem(ACTIVE_TAB_KEY);
        return activeTab === TAB_ID;
    }

    // Register this tab as active
    function registerActiveTab() {
        localStorage.setItem(ACTIVE_TAB_KEY, TAB_ID);
        console.log('✅ Tab registered as active:', TAB_ID);
    }

    // Get session data
    function getSessionData() {
        try {
            const data = sessionStorage.getItem(SESSION_KEY);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            return null;
        }
    }

    // Store session data
    function storeSessionData(userData) {
        const data = {
            ...userData,
            tabId: TAB_ID,
            timestamp: Date.now()
        };
        sessionStorage.setItem(SESSION_KEY, JSON.stringify(data));
        localStorage.setItem(ACTIVE_TAB_KEY, TAB_ID);
        console.log('💾 Session stored for tab:', TAB_ID);
    }

    // Clear session data
    function clearSessionData() {
        sessionStorage.removeItem(SESSION_KEY);
        if (localStorage.getItem(ACTIVE_TAB_KEY) === TAB_ID) {
            localStorage.removeItem(ACTIVE_TAB_KEY);
        }
        console.log('🗑️ Session cleared for tab:', TAB_ID);
    }

    // Broadcast logout
    function broadcastLogout() {
        try {
            localStorage.setItem('edu_logout_event', JSON.stringify({
                tabId: TAB_ID,
                timestamp: Date.now()
            }));
            setTimeout(() => {
                localStorage.removeItem('edu_logout_event');
            }, 1000);
        } catch (e) {
            console.error('Logout broadcast error:', e);
        }
    }

    // === MAIN LOGIC ===

    // Listen for storage changes from other tabs
    window.addEventListener('storage', function(e) {
        console.log('📡 Storage event:', e.key, e.newValue);

        // Check if another tab registered as active
        if (e.key === ACTIVE_TAB_KEY) {
            const activeTab = e.newValue;
            
            if (activeTab && activeTab !== TAB_ID) {
                const mySession = getSessionData();
                
                if (mySession) {
                    // We have a session but another tab is active
                    console.log('⚠️ Another tab is active:', activeTab);
                    
                    // Check if we're on a dashboard page
                    const isDashboard = window.location.pathname.includes('dashboard') || 
                                      window.location.pathname.includes('teacher') ||
                                      window.location.pathname.includes('admin');
                    
                    if (isDashboard) {
                        // Show warning and redirect to login
                        alert('⚠️ You logged in from another tab.\n\nThis tab will now redirect to login page.');
                        clearSessionData();
                        window.location.href = '/login/';
                    }
                }
            }
        }

        // Check for logout event
        if (e.key === 'edu_logout_event') {
            if (e.newValue) {
                try {
                    const logoutData = JSON.parse(e.newValue);
                    if (logoutData.tabId !== TAB_ID) {
                        const mySession = getSessionData();
                        if (mySession) {
                            console.log('🚪 Logout detected from another tab');
                            clearSessionData();
                            window.location.href = '/login/';
                        }
                    }
                } catch (e) {
                    console.error('Logout event error:', e);
                }
            }
        }
    });

    // === INITIALIZATION ===

    // Run when page loads
    document.addEventListener('DOMContentLoaded', function() {
        console.log('🚀 Page loaded - Tab:', TAB_ID);
        
        const currentPath = window.location.pathname;
        const isLoginPage = currentPath.includes('/login/') || currentPath === '/';
        const isDashboardPage = currentPath.includes('dashboard') || 
                               currentPath.includes('teacher') ||
                               currentPath.includes('admin') ||
                               currentPath.includes('head');

        // If on login page, clear session
        if (isLoginPage) {
            clearSessionData();
            registerActiveTab();
            return;
        }

        // Check if user is authenticated (from Django)
        const isAuthenticated = document.body.dataset.userAuthenticated === 'true';
        
        if (isAuthenticated && isDashboardPage) {
            // Check if this tab is active
            const activeTab = localStorage.getItem(ACTIVE_TAB_KEY);
            
            if (activeTab && activeTab !== TAB_ID) {
                // Another tab is active - redirect to login
                console.log('🔒 Another tab is active, redirecting...');
                alert('⚠️ This session is being used in another tab.\n\nYou will be redirected to login.');
                clearSessionData();
                window.location.href = '/login/';
                return;
            }
            
            // Register this tab as active
            registerActiveTab();
            
            // Store session data from Django template
            const userData = {
                userId: document.body.dataset.userId || '',
                username: document.body.dataset.username || '',
                role: document.body.dataset.userRole || ''
            };
            
            if (userData.userId) {
                storeSessionData(userData);
            }
        }

        // Check every 2 seconds if this tab is still active
        setInterval(function() {
            const activeTab = localStorage.getItem(ACTIVE_TAB_KEY);
            const isDashboard = window.location.pathname.includes('dashboard') || 
                               window.location.pathname.includes('teacher') ||
                               window.location.pathname.includes('admin');
            
            if (isDashboard && activeTab && activeTab !== TAB_ID) {
                console.log('⚠️ Tab hijacked! Redirecting...');
                alert('⚠️ Another tab has taken over this session.\n\nYou will be redirected to login.');
                clearSessionData();
                window.location.href = '/login/';
            }
        }, 3000);
    });

    // Expose functions globally
    window.TabIsolation = {
        TAB_ID: TAB_ID,
        isActive: isThisTabActive,
        register: registerActiveTab,
        storeSession: storeSessionData,
        clearSession: clearSessionData,
        getSession: getSessionData,
        broadcastLogout: broadcastLogout
    };

})();