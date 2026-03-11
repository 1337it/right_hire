// Manage active state for sidebar items
(function() {
    'use strict';

    const DEBUG = true; // Set to true to enable console logging

    function log(...args) {
        if (DEBUG) console.log('[sidebar-active]', ...args);
    }

    // Function to update active sidebar item based on current route
    function updateActiveSidebarItem() {
        // Get all sidebar item containers
        const sidebarItems = document.querySelectorAll('.sidebar-item-container');

        if (!sidebarItems.length) {
            log('No sidebar items found');
            return;
        }

        // Get current route - try multiple methods
        let currentRoute = '';
        if (window.frappe && frappe.get_route_str) {
            currentRoute = frappe.get_route_str();
        } else if (window.frappe && frappe.get_route) {
            currentRoute = frappe.get_route().join('/');
        } else {
            currentRoute = window.location.hash.replace(/^#/, '');
        }

        log('Current route:', currentRoute);
        log('Found sidebar items:', sidebarItems.length);

        // Remove active class from all items
        sidebarItems.forEach(item => {
            item.classList.remove('active');
            const anchor = item.querySelector('.item-anchor');
            if (anchor) {
                anchor.classList.remove('selected');
            }
            const content = item.querySelector('.sidebar-item-content');
            if (content) {
                content.classList.remove('selected');
                content.classList.remove('active-menu-item');
                content.removeAttribute('data-active');
                // Also remove inline styles that might have been set
                content.style.backgroundColor = '';
                content.style.borderRadius = '';
            }
        });

        // Find and activate the matching item
        let foundMatch = false;
        sidebarItems.forEach(item => {
            const anchor = item.querySelector('.item-anchor');
            const content = item.querySelector('.sidebar-item-content');

            if (!anchor && !content) {
                log('Item has no anchor or content');
                return;
            }

            // Get the route from various possible sources
            let itemRoute = null;

            // Try anchor href
            if (anchor) {
                itemRoute = anchor.getAttribute('href');
            }

            // Try data-route attribute
            if (!itemRoute) {
                itemRoute = item.getAttribute('data-route') ||
                           (anchor && anchor.getAttribute('data-route')) ||
                           (content && content.getAttribute('data-route'));
            }

            // Try data-name attribute (for doctypes)
            if (!itemRoute) {
                const itemName = item.getAttribute('data-item-label') ||
                                item.getAttribute('data-name');
                if (itemName) {
                    // Check if current route includes this item name
                    if (currentRoute.toLowerCase().includes(itemName.toLowerCase().replace(/\s+/g, '-')) ||
                        currentRoute.toLowerCase().includes(itemName.toLowerCase().replace(/\s+/g, '%20')) ||
                        currentRoute.toLowerCase().includes(itemName.toLowerCase())) {
                        itemRoute = currentRoute;
                    }
                }
            }

            if (!itemRoute) {
                log('Item has no route');
                return;
            }

            // Remove leading # if present
            itemRoute = itemRoute.replace(/^#/, '');

            log('Checking item route:', itemRoute, 'against current:', currentRoute);

            // Check if this item matches the current route
            // Match exact route or if current route starts with item route
            const isMatch = itemRoute === currentRoute ||
                           currentRoute.startsWith(itemRoute + '/') ||
                           itemRoute.startsWith(currentRoute);

            if (isMatch) {
                log('Found match:', itemRoute);
                item.classList.add('active');
                if (anchor) anchor.classList.add('selected');
                if (content) {
                    content.classList.add('selected');
                    content.classList.add('active-menu-item');
                    content.setAttribute('data-active', 'true');
                    // Also set inline styles to match sidebar_menu behavior
                    content.style.backgroundColor = '#f3f3f3';
                    content.style.borderRadius = '6px';
                }
                foundMatch = true;
            }
        });

        log('Match found:', foundMatch);
    }

    // Initialize on DOM ready
    function init() {
        log('Initializing sidebar active manager');

        // Update immediately
        updateActiveSidebarItem();

        // Update after a short delay (in case DOM is still loading)
        setTimeout(updateActiveSidebarItem, 100);
        setTimeout(updateActiveSidebarItem, 300);
        setTimeout(updateActiveSidebarItem, 500);

        // Listen to Frappe route changes
        if (frappe && frappe.router && frappe.router.on) {
            log('Attaching to frappe.router.on("change")');
            frappe.router.on('change', () => {
                log('Route changed via frappe.router');
                // Multiple attempts with different delays
                setTimeout(updateActiveSidebarItem, 10);
                setTimeout(updateActiveSidebarItem, 50);
                setTimeout(updateActiveSidebarItem, 150);
                setTimeout(updateActiveSidebarItem, 300);
            });
        }

        // Fallback: listen to hashchange
        window.addEventListener('hashchange', () => {
            log('Route changed via hashchange');
            setTimeout(updateActiveSidebarItem, 10);
            setTimeout(updateActiveSidebarItem, 50);
            setTimeout(updateActiveSidebarItem, 150);
        });

        // Also update when page changes (for ajax navigation)
        $(document).on('page-change', () => {
            log('Page changed via jQuery page-change event');
            setTimeout(updateActiveSidebarItem, 10);
            setTimeout(updateActiveSidebarItem, 50);
            setTimeout(updateActiveSidebarItem, 150);
        });

        // Listen to frappe's render_page event
        frappe.ui.pages && $(frappe.ui.pages).on('render_page', () => {
            log('Page rendered via frappe.ui.pages');
            setTimeout(updateActiveSidebarItem, 10);
            setTimeout(updateActiveSidebarItem, 50);
        });

        // Observe the main page container for content changes
        const observePageContent = () => {
            const pageContainer = document.querySelector('.page-container, .layout-main-section-wrapper, #body');
            if (pageContainer) {
                log('Observing page container for content changes');
                const contentObserver = new MutationObserver((mutations) => {
                    // Check if this is a significant change (not just style updates)
                    const hasSignificantChange = mutations.some(m =>
                        m.type === 'childList' && m.addedNodes.length > 0
                    );
                    if (hasSignificantChange) {
                        log('Page content changed via MutationObserver');
                        setTimeout(updateActiveSidebarItem, 10);
                        setTimeout(updateActiveSidebarItem, 100);
                    }
                });
                contentObserver.observe(pageContainer, {
                    childList: true,
                    subtree: false // Only watch direct children
                });
            } else {
                setTimeout(observePageContent, 500);
            }
        };
        observePageContent();

        // Watch for URL changes using setInterval as last resort
        let lastUrl = window.location.href;
        setInterval(() => {
            const currentUrl = window.location.href;
            if (currentUrl !== lastUrl) {
                log('URL changed detected via polling:', currentUrl);
                lastUrl = currentUrl;
                setTimeout(updateActiveSidebarItem, 10);
                setTimeout(updateActiveSidebarItem, 100);
            }
        }, 500);

        // Watch for sidebar DOM changes (in case items are dynamically added)
        let debounceTimer = null;
        const observer = new MutationObserver(() => {
            // Debounce to avoid too many updates
            if (debounceTimer) clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                log('Sidebar DOM changed');
                updateActiveSidebarItem();
            }, 100);
        });

        // Observe the workspace sidebar
        const observeWorkspaceSidebar = () => {
            const workspaceSidebar = document.querySelector('#page-Workspaces .layout-side-section');
            if (workspaceSidebar) {
                log('Found workspace sidebar, observing...');
                observer.observe(workspaceSidebar, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: ['class']
                });
            } else {
                log('Workspace sidebar not found, retrying...');
                // Retry if sidebar not found yet
                setTimeout(observeWorkspaceSidebar, 500);
            }
        };

        observeWorkspaceSidebar();

        // Also observe the entire document for new sidebars
        const docObserver = new MutationObserver(() => {
            const sidebar = document.querySelector('.sidebar-item-container');
            if (sidebar) {
                observeWorkspaceSidebar();
            }
        });
        docObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Also run when Frappe is ready
    $(document).ready(() => {
        log('jQuery ready');
        setTimeout(init, 100);
        setTimeout(init, 500);
        setTimeout(init, 1000);
    });

    // Frappe app ready
    if (window.frappe) {
        frappe.ready(() => {
            log('Frappe ready');
            setTimeout(init, 100);
        });
    }
})();
