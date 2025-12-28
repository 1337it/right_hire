// Add back button when page loads
$(document).ready(function() {
    // Wait a bit for page-head to be rendered
    setTimeout(add_navbar_back_button, 500);

    // Set up continuous monitoring
    setupBackButtonMonitoring();
});

// Listen for hash changes (route changes)
$(window).on('hashchange', function() {
    setTimeout(add_navbar_back_button, 300);
});

// Listen for Frappe route changes
if (typeof frappe !== 'undefined') {
    frappe.router && frappe.router.on && frappe.router.on('change', function() {
        setTimeout(add_navbar_back_button, 300);
    });
}

function setupBackButtonMonitoring() {
    // Check every 500ms and add button to visible page-heads
    setInterval(function() {
        add_navbar_back_button();
    }, 500);
}

function add_navbar_back_button() {
    // Create back button HTML with inline SVG
    const backButton = `
        <button class="page-head-back-btn btn btn-default btn-sm" title="Go Back" style="margin-right: 10px;">
            <svg class="icon icon-sm" style="width: 16px; height: 16px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;">
                <path d="M19 12H5M12 19l-7-7 7-7"></path>
            </svg>
        </button>
    `;

    // Find all visible page-heads (not display:none)
    $('.page-head:visible').each(function() {
        const $pageHead = $(this);

        // Check if this page-head already has a back button
        if ($pageHead.find('.page-head-back-btn').length === 0) {
            // Prepend the button
            $pageHead.prepend(backButton);

            // Add click handler to the newly added button
            $pageHead.find('.page-head-back-btn').off('click').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                window.history.back();
                return false;
            });
        }
    });
}
