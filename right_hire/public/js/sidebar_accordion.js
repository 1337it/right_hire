// Sidebar Accordion Behavior for Right Hire
// Makes sidebar menu items close others when one is opened

(function() {
    'use strict';

    // Guard to prevent multiple initializations
    if (window.__SIDEBAR_ACCORDION_INITIALIZED) {
        return;
    }
    window.__SIDEBAR_ACCORDION_INITIALIZED = true;

    function initSidebarAccordion() {
        // Wait for sidebar to be injected
        const checkSidebar = setInterval(function() {
            const $sidebar = $('.desk-sidebar');

            if ($sidebar.length && $sidebar.find('.sidebar-item-container').length > 0) {
                clearInterval(checkSidebar);
                setupAccordion($sidebar);
            }
        }, 500);

        // Clear interval after 10 seconds to prevent infinite checking
        setTimeout(function() {
            clearInterval(checkSidebar);
        }, 10000);
    }

    function setupAccordion($sidebar) {
        // Only set up once per sidebar element
        if ($sidebar.data('accordion-initialized')) {
            return;
        }
        $sidebar.data('accordion-initialized', true);

        // Only close all if more than one accordion is open
        const $openItems = $sidebar.find('.btn-submenu-toggle[aria-expanded="true"]');

        if ($openItems.length > 1) {
            // Close all accordion items
            $sidebar.find('.btn-submenu-toggle').each(function() {
                const $toggle = $(this);
                const $item = $toggle.closest('.sidebar-item-container');
                const $children = $item.find('> .sidebar-children');

                $toggle.attr('aria-expanded', 'false');
                $toggle.find('svg.toggle-arrow').css({
                    transform: 'rotate(0deg)',
                    transformOrigin: 'center'
                });
                $children.hide();
            });
        }

        // Remove all existing handlers and href from items with children
        $sidebar.find('.sidebar-item-content').each(function() {
            const $content = $(this);
            const $anchor = $content.find('.item-anchor');
            const $toggle = $content.find('.btn-submenu-toggle');

            if ($toggle.length > 0) {
                // Remove ALL existing click handlers
                $anchor.off('click');
                $toggle.off('click');

                // Remove href="#" to prevent navigation
                if ($anchor.attr('href') === '#') {
                    $anchor.removeAttr('href');
                }
                $anchor.css('cursor', 'pointer');
            }
        });

        // Fix query-report link click handlers from custom_sidebar.js
        $sidebar.find('.item-anchor').each(function() {
            const $anchor = $(this);
            const href = $anchor.attr('href');

            if (href && href.includes('/query-report/')) {
                $anchor.off('click').on('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();

                    // Extract report name from href
                    const reportName = href.replace(/^\/app\/query-report\//, '').replace(/-/g, ' ');
                    // Capitalize each word
                    const formattedName = reportName.split(' ').map(word =>
                        word.charAt(0).toUpperCase() + word.slice(1)
                    ).join(' ');

                    frappe.set_route('query-report', formattedName);
                });
            }
        });

        // Attach accordion listener on the entire row
        $sidebar.off('click.accordion').on('click.accordion', '.sidebar-item-content', function(e) {
            const $itemContent = $(this);
            const $item = $itemContent.closest('.sidebar-item-container');
            const $toggleBtn = $itemContent.find('.btn-submenu-toggle');

            // Only handle accordion if this item has children
            if ($toggleBtn.length === 0) {
                return; // No submenu, let the link work normally
            }

            // Stop ALL other handlers and prevent default behavior
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();

            const $children = $item.find('> .sidebar-children');
            const isExpanded = $toggleBtn.attr('aria-expanded') === 'true';

            // Close all other items
            $sidebar.find('.btn-submenu-toggle').each(function() {
                const $toggle = $(this);
                const $otherItem = $toggle.closest('.sidebar-item-container');
                const $otherChildren = $otherItem.find('> .sidebar-children');

                if ($otherItem[0] !== $item[0]) {
                    $toggle.attr('aria-expanded', 'false');
                    $toggle.find('svg.toggle-arrow').css({
                        transform: 'rotate(0deg)',
                        transformOrigin: 'center'
                    });
                    $otherChildren.hide();
                }
            });

            // Toggle the clicked item
            $toggleBtn.attr('aria-expanded', !isExpanded);
            $toggleBtn.find('svg.toggle-arrow').css({
                transform: !isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                transformOrigin: 'center'
            });
            $children.toggle(!isExpanded);

            return false;
        });

        console.log('[Right Hire] Sidebar accordion initialized');
    }

    // Initialize when DOM is ready
    $(document).ready(function() {
        setTimeout(initSidebarAccordion, 1000);
    });

    // Re-initialize when custom sidebar is reloaded
    if (window.frappe && frappe.realtime) {
        frappe.realtime.on('custom_sidebar_menu_updated', function() {
            setTimeout(function() {
                const $sidebar = $('.desk-sidebar');
                if ($sidebar.length) {
                    // Reset the flag when sidebar is reloaded
                    $sidebar.removeData('accordion-initialized');
                    setupAccordion($sidebar);
                }
            }, 1000);
        });
    }

    // Re-initialize on route changes
    if (window.frappe && frappe.router) {
        frappe.router.on('change', function() {
            setTimeout(function() {
                const $sidebar = $('.desk-sidebar');
                if ($sidebar.length && $sidebar.find('.sidebar-item-container').length > 0) {
                    // Reset the flag on route change
                    $sidebar.removeData('accordion-initialized');
                    setupAccordion($sidebar);
                }
            }, 1500);
        });
    }
})();
