// Custom Icon Sets for Right Hire
// Adds Font Awesome, Material Icons, Heroicons, Feather, Lucide, and Bootstrap Icons

(function() {
    'use strict';

    // Wait for Frappe to be ready
    function initIconSets() {
        if (!window.frappe) {
            setTimeout(initIconSets, 100);
            return;
        }

        console.log('[Right Hire] Loading custom icon sets...');

        // Add icon sprite sheets to the page
        loadIconSprites();

        // Register icons with Frappe's icon picker
        registerIconsWithFrappe();

        console.log('[Right Hire] Custom icon sets loaded');
    }

    function registerIconsWithFrappe() {
        // Watch for icon picker popover to appear in DOM
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.classList && node.classList.contains('icon-picker-popover')) {
                        // Icon picker popover appeared
                        setTimeout(() => injectCustomIcons(node), 100);
                    }
                });
            });
        });

        // Observe document body for popover additions
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('[Right Hire] Icon picker observer installed');
    }

    function injectCustomIcons(popover) {
        const $popover = $(popover);

        const $iconSection = $popover.find('.icon-section');
        if (!$iconSection.length) return;

        const $icons = $iconSection.find('.icons');
        if (!$icons.length) return;

        // Check if already injected
        if ($icons.find('.custom-icon-header').length > 0) return;

        // Font Awesome icons (outline/regular only)
        const faIcons = [
            // General
            'home', 'user', 'users', 'user-circle', 'user-cog', 'cog', 'sliders-h', 'bars',
            'heart', 'star', 'bookmark', 'bell', 'flag',
            // Communication
            'envelope', 'envelope-open', 'comment', 'comments', 'phone', 'mobile-alt',
            'video', 'at', 'hashtag', 'share', 'share-alt', 'paper-plane',
            // Files & Documents
            'file', 'file-alt', 'file-pdf', 'file-word', 'file-excel', 'file-powerpoint',
            'file-image', 'file-code', 'folder', 'folder-open', 'copy', 'paste',
            // Time & Calendar
            'calendar', 'calendar-alt', 'calendar-check', 'calendar-plus', 'clock',
            'hourglass', 'stopwatch', 'history',
            // Media
            'image', 'images', 'camera', 'video', 'film', 'music', 'headphones',
            'microphone', 'play', 'pause', 'stop',
            // Actions
            'search', 'filter', 'sort', 'download', 'upload', 'cloud-download-alt',
            'cloud-upload-alt', 'sync', 'redo', 'undo', 'refresh',
            // Edit & Create
            'plus', 'plus-circle', 'minus', 'minus-circle', 'edit', 'pen', 'pencil-alt',
            'trash', 'trash-alt', 'eraser', 'cut', 'scissors',
            // Status & Indicators
            'check', 'check-circle', 'times', 'times-circle', 'exclamation',
            'exclamation-circle', 'exclamation-triangle', 'question', 'question-circle',
            'info', 'info-circle',
            // Navigation
            'arrow-left', 'arrow-right', 'arrow-up', 'arrow-down', 'chevron-left',
            'chevron-right', 'chevron-up', 'chevron-down', 'angle-left', 'angle-right',
            'angle-up', 'angle-down', 'caret-left', 'caret-right', 'caret-up', 'caret-down',
            // Location & Maps
            'map', 'map-marker-alt', 'location-arrow', 'compass', 'globe', 'globe-americas',
            // Business & Office
            'briefcase', 'building', 'chart-line', 'chart-bar', 'chart-pie', 'chart-area',
            'table', 'clipboard', 'clipboard-list', 'clipboard-check', 'tasks', 'list',
            'list-ul', 'list-ol', 'calculator', 'receipt',
            // Vehicles
            'car', 'car-alt', 'truck', 'shuttle-van', 'bus', 'taxi', 'motorcycle',
            'bicycle', 'plane', 'helicopter', 'ship', 'train', 'subway', 'tram',
            // Money & Commerce
            'dollar-sign', 'euro-sign', 'pound-sign', 'money-bill', 'money-bill-wave',
            'coins', 'credit-card', 'wallet', 'shopping-cart', 'shopping-bag',
            'cash-register', 'percent', 'tag', 'tags',
            // Security
            'lock', 'lock-open', 'unlock', 'key', 'shield-alt', 'user-shield',
            'eye', 'eye-slash', 'fingerprint',
            // Tech & Development
            'code', 'terminal', 'database', 'server', 'hdd', 'laptop', 'desktop',
            'tablet-alt', 'mobile', 'wifi', 'ethernet', 'network-wired', 'plug',
            // Tools & Settings
            'wrench', 'hammer', 'screwdriver', 'tools', 'cogs', 'sliders-h',
            // Layout & Design
            'th', 'th-large', 'th-list', 'border-all', 'columns', 'grip-horizontal',
            'grip-vertical', 'align-left', 'align-center', 'align-right', 'align-justify',
            // Misc
            'anchor', 'award', 'trophy', 'medal', 'crown', 'gem', 'lightbulb',
            'magic', 'gift', 'birthday-cake', 'pizza-slice', 'coffee', 'mug-hot'
        ];

        // Material Icons (outline only)
        const miIcons = [
            // General
            'home', 'home_work', 'settings', 'tune', 'build', 'construction', 'person',
            'people', 'group', 'person_outline', 'account_circle', 'manage_accounts',
            'favorite_border', 'favorite', 'star_border', 'star', 'bookmark_border', 'bookmark',
            // Communication
            'email', 'mail_outline', 'send', 'forward_to_inbox', 'mark_email_read',
            'phone', 'call', 'smartphone', 'phone_android', 'phone_iphone',
            'chat', 'chat_bubble_outline', 'message', 'textsms', 'videocam',
            // Files
            'insert_drive_file', 'description', 'article', 'topic', 'folder',
            'folder_open', 'create_new_folder', 'upload_file', 'download', 'cloud_download',
            'cloud_upload', 'attach_file', 'attachment',
            // Time
            'event', 'event_note', 'calendar_today', 'date_range', 'schedule',
            'access_time', 'alarm', 'timer', 'hourglass_empty', 'history',
            // Media
            'photo', 'photo_camera', 'camera_alt', 'videocam', 'movie', 'music_note',
            'audiotrack', 'headphones', 'headset', 'mic', 'mic_none',
            // Actions
            'search', 'filter_list', 'sort', 'download', 'upload', 'cloud_sync',
            'sync', 'refresh', 'autorenew', 'cached',
            // Edit
            'add', 'add_circle_outline', 'remove', 'remove_circle_outline', 'edit',
            'create', 'mode_edit', 'delete', 'delete_outline', 'delete_forever',
            // Status
            'check', 'check_circle_outline', 'check_circle', 'done', 'done_all',
            'close', 'cancel', 'error_outline', 'warning', 'info_outline', 'help_outline',
            // Navigation
            'arrow_back', 'arrow_forward', 'arrow_upward', 'arrow_downward',
            'chevron_left', 'chevron_right', 'expand_less', 'expand_more',
            'north', 'south', 'east', 'west',
            // Location
            'map', 'place', 'location_on', 'near_me', 'navigation', 'explore',
            'public', 'language', 'travel_explore',
            // Business
            'business', 'business_center', 'work', 'work_outline', 'assessment',
            'bar_chart', 'show_chart', 'trending_up', 'trending_down', 'analytics',
            'table_chart', 'pie_chart', 'insert_chart', 'assignment', 'task',
            'checklist', 'list', 'view_list', 'receipt', 'calculate',
            // Vehicles
            'directions_car', 'car_rental', 'local_shipping', 'local_taxi',
            'airport_shuttle', 'directions_bus', 'two_wheeler', 'pedal_bike',
            'flight', 'flight_takeoff', 'flight_land', 'directions_boat', 'train',
            // Money
            'payments', 'payment', 'credit_card', 'account_balance_wallet',
            'attach_money', 'euro_symbol', 'currency_pound', 'shopping_cart',
            'shopping_bag', 'store', 'local_atm', 'receipt_long', 'discount',
            // Security
            'lock', 'lock_open', 'vpn_key', 'key', 'shield', 'security',
            'verified_user', 'visibility', 'visibility_off', 'fingerprint',
            // Tech
            'code', 'terminal', 'storage', 'dns', 'cloud', 'computer', 'laptop',
            'tablet', 'smartphone', 'wifi', 'router', 'devices', 'usb',
            // Tools
            'build', 'handyman', 'engineering', 'plumbing', 'electrical_services',
            'home_repair_service', 'settings_applications', 'display_settings',
            // Layout
            'dashboard', 'grid_view', 'view_module', 'view_comfy', 'view_compact',
            'table_rows', 'table_chart', 'splitscreen', 'format_align_left',
            'format_align_center', 'format_align_right', 'format_align_justify'
        ];

        // Bootstrap Icons (outline only)
        const biIcons = [
            // General
            'house', 'house-door', 'gear', 'sliders', 'list', 'person', 'people',
            'person-circle', 'heart', 'star', 'bookmark', 'bell', 'flag',
            // Communication
            'envelope', 'envelope-open', 'chat', 'chat-dots', 'telephone', 'phone',
            'webcam', 'at', 'hash', 'share', 'send', 'arrow-up-right-circle',
            // Files
            'file-earmark', 'file-earmark-text', 'file-earmark-pdf', 'file-earmark-word',
            'file-earmark-excel', 'file-earmark-ppt', 'file-earmark-image',
            'file-earmark-code', 'folder', 'folder-open', 'clipboard', 'files',
            // Time
            'calendar', 'calendar-event', 'calendar-check', 'calendar-plus', 'clock',
            'clock-history', 'hourglass', 'stopwatch', 'alarm',
            // Media
            'image', 'images', 'camera', 'camera-video', 'film', 'music-note-beamed',
            'headphones', 'mic', 'play-circle', 'pause-circle', 'stop-circle',
            // Actions
            'search', 'funnel', 'sort-down', 'download', 'upload', 'cloud-download',
            'cloud-upload', 'arrow-clockwise', 'arrow-counterclockwise', 'arrow-repeat',
            // Edit
            'plus', 'plus-circle', 'dash', 'dash-circle', 'pencil', 'pen',
            'trash', 'trash3', 'eraser', 'scissors', 'x', 'x-circle',
            // Status
            'check', 'check-circle', 'check-all', 'x', 'x-circle', 'exclamation',
            'exclamation-circle', 'exclamation-triangle', 'question', 'question-circle',
            'info', 'info-circle',
            // Navigation
            'arrow-left', 'arrow-right', 'arrow-up', 'arrow-down', 'chevron-left',
            'chevron-right', 'chevron-up', 'chevron-down', 'caret-left', 'caret-right',
            'caret-up', 'caret-down',
            // Location
            'map', 'geo-alt', 'compass', 'globe', 'globe-americas', 'signpost',
            // Business
            'briefcase', 'building', 'graph-up', 'bar-chart', 'pie-chart',
            'table', 'clipboard-data', 'clipboard-check', 'list-check', 'calculator',
            'receipt', 'cash-stack',
            // Vehicles
            'car-front', 'truck', 'bus-front', 'taxi-front', 'bicycle', 'scooter',
            'airplane', 'train-front', 'subway', 'ev-front',
            // Money
            'currency-dollar', 'currency-euro', 'currency-pound', 'cash', 'credit-card',
            'wallet', 'cart', 'bag', 'shop', 'tag', 'tags', 'percent',
            // Security
            'lock', 'unlock', 'key', 'shield', 'shield-check', 'eye', 'eye-slash',
            'fingerprint',
            // Tech
            'code', 'terminal', 'database', 'server', 'hdd', 'laptop', 'pc-display',
            'tablet', 'phone', 'wifi', 'router', 'plug', 'usb',
            // Tools
            'wrench', 'hammer', 'screwdriver', 'tools', 'gear-wide-connected',
            // Layout
            'grid', 'grid-3x3', 'table', 'columns', 'layout-split', 'text-left',
            'text-center', 'text-right', 'justify'
        ];

        // Create Font Awesome header and icons
        const $faHeader = $(`<div class="custom-icon-header" style="width: 100%; margin-top: 20px; margin-bottom: 10px; padding: 8px; background: #f3f4f6; border-radius: 4px; font-weight: 600; color: #374151;">Font Awesome Icons</div>`);

        $icons.append($faHeader);

        faIcons.forEach(icon => {
            const $iconWrapper = $(`
                <div id="fa-${icon}" class="icon-wrapper" style="cursor: pointer;">
                    <i class="fas fa-${icon}" style="font-size: 20px;"></i>
                </div>
            `);

            $iconWrapper.on('click', function(e) {
                e.stopPropagation();
                // Find the input field and set the value
                const $input = $('.frappe-control[data-fieldtype="Icon"] input[data-fieldtype="Icon"]');
                if ($input.length) {
                    $input.val(`fa-${icon}`).trigger('change');
                    // Hide popover
                    $('.icon-picker-popover').remove();
                }
            });

            $icons.append($iconWrapper);
        });

        // Create Material Icons header and icons
        const $miHeader = $(`<div class="custom-icon-header" style="width: 100%; margin-top: 20px; margin-bottom: 10px; padding: 8px; background: #f3f4f6; border-radius: 4px; font-weight: 600; color: #374151;">Material Icons</div>`);
        $icons.append($miHeader);

        miIcons.forEach(icon => {
            const $iconWrapper = $(`
                <div id="mi-${icon}" class="icon-wrapper" style="cursor: pointer;">
                    <span class="material-icons" style="font-size: 20px;">${icon}</span>
                </div>
            `);

            $iconWrapper.on('click', function(e) {
                e.stopPropagation();
                const $input = $('.frappe-control[data-fieldtype="Icon"] input[data-fieldtype="Icon"]');
                if ($input.length) {
                    $input.val(`mi-${icon}`).trigger('change');
                    $('.icon-picker-popover').remove();
                }
            });

            $icons.append($iconWrapper);
        });

        // Create Bootstrap Icons header and icons
        const $biHeader = $(`<div class="custom-icon-header" style="width: 100%; margin-top: 20px; margin-bottom: 10px; padding: 8px; background: #f3f4f6; border-radius: 4px; font-weight: 600; color: #374151;">Bootstrap Icons</div>`);
        $icons.append($biHeader);

        biIcons.forEach(icon => {
            const $iconWrapper = $(`
                <div id="bi-${icon}" class="icon-wrapper" style="cursor: pointer;">
                    <i class="bi bi-${icon}" style="font-size: 20px;"></i>
                </div>
            `);

            $iconWrapper.on('click', function(e) {
                e.stopPropagation();
                const $input = $('.frappe-control[data-fieldtype="Icon"] input[data-fieldtype="Icon"]');
                if ($input.length) {
                    $input.val(`bi-${icon}`).trigger('change');
                    $('.icon-picker-popover').remove();
                }
            });

            $icons.append($iconWrapper);
        });

        console.log('[Right Hire] Injected custom icons into picker');
    }

    function loadIconSprites() {
        // Create a container for icon sprites
        let spriteContainer = document.getElementById('custom-icon-sprites');
        if (!spriteContainer) {
            spriteContainer = document.createElement('div');
            spriteContainer.id = 'custom-icon-sprites';
            spriteContainer.style.display = 'none';
            document.body.insertBefore(spriteContainer, document.body.firstChild);
        }

        // Load icon sets via CDN
        loadIconSet('bootstrap-icons', 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.svg');
        loadIconSet('feather', 'https://cdn.jsdelivr.net/npm/feather-icons@4.29.1/dist/feather-sprite.svg');

        // Load Font Awesome via stylesheet
        loadStylesheet('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

        // Load Material Icons via stylesheet
        loadStylesheet('https://fonts.googleapis.com/icon?family=Material+Icons');
        loadStylesheet('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');

        // Add Heroicons, Lucide via inline SVG system
        setupInlineIconSystem();
    }

    function loadIconSet(name, url) {
        fetch(url)
            .then(response => response.text())
            .then(svgContent => {
                const container = document.getElementById('custom-icon-sprites');
                const wrapper = document.createElement('div');
                wrapper.id = `icon-sprite-${name}`;
                wrapper.innerHTML = svgContent;
                container.appendChild(wrapper);
                console.log(`[Right Hire] Loaded ${name} icons`);
            })
            .catch(err => {
                console.warn(`[Right Hire] Failed to load ${name} icons:`, err);
            });
    }

    function loadStylesheet(url) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = url;
        document.head.appendChild(link);
    }

    function setupInlineIconSystem() {
        // Create helper functions for using custom icons
        if (!window.righthire) {
            window.righthire = {};
        }

        // Helper to create icon elements
        window.righthire.icon = function(iconName, options = {}) {
            const opts = Object.assign({
                size: 'md',
                class: '',
                style: ''
            }, options);

            let html = '';

            // Font Awesome
            if (iconName.startsWith('fa-')) {
                const type = iconName.includes('fab-') ? 'fab' :
                           iconName.includes('far-') ? 'far' : 'fas';
                const icon = iconName.replace(/^(fa[brs]?-)?/, '');
                html = `<i class="${type} fa-${icon} ${opts.class}" style="${opts.style}"></i>`;
            }
            // Material Icons
            else if (iconName.startsWith('mi-')) {
                const icon = iconName.replace(/^mi-/, '').replace(/-/g, '_');
                html = `<span class="material-icons ${opts.class}" style="${opts.style}">${icon}</span>`;
            }
            // Material Symbols
            else if (iconName.startsWith('ms-')) {
                const icon = iconName.replace(/^ms-/, '').replace(/-/g, '_');
                html = `<span class="material-symbols-outlined ${opts.class}" style="${opts.style}">${icon}</span>`;
            }
            // Bootstrap Icons
            else if (iconName.startsWith('bi-')) {
                html = `<i class="bi ${iconName} ${opts.class}" style="${opts.style}"></i>`;
            }
            // Feather Icons (use SVG from sprite)
            else if (iconName.startsWith('feather-')) {
                const icon = iconName.replace(/^feather-/, '');
                html = `<svg class="feather feather-${icon} ${opts.class}" style="${opts.style}">
                    <use href="#feather-${icon}"/>
                </svg>`;
            }
            // Heroicons
            else if (iconName.startsWith('hero-')) {
                const icon = iconName.replace(/^hero-/, '');
                html = createHeroicon(icon, opts);
            }
            // Lucide
            else if (iconName.startsWith('lucide-')) {
                const icon = iconName.replace(/^lucide-/, '');
                html = createLucideIcon(icon, opts);
            }

            return html;
        };

        // Add CSS for icon sizing
        const style = document.createElement('style');
        style.textContent = `
            /* Custom Icon Sizes */
            .icon-xs { width: 12px; height: 12px; }
            .icon-sm { width: 16px; height: 16px; }
            .icon-md { width: 20px; height: 20px; }
            .icon-lg { width: 24px; height: 24px; }
            .icon-xl { width: 32px; height: 32px; }

            /* Material Icons sizing */
            .material-icons.icon-xs,
            .material-symbols-outlined.icon-xs { font-size: 12px; }
            .material-icons.icon-sm,
            .material-symbols-outlined.icon-sm { font-size: 16px; }
            .material-icons.icon-md,
            .material-symbols-outlined.icon-md { font-size: 20px; }
            .material-icons.icon-lg,
            .material-symbols-outlined.icon-lg { font-size: 24px; }
            .material-icons.icon-xl,
            .material-symbols-outlined.icon-xl { font-size: 32px; }

            /* Font Awesome sizing */
            .fa-xs { font-size: 12px; }
            .fa-sm { font-size: 16px; }
            .fa-md { font-size: 20px; }
            .fa-lg { font-size: 24px; }
            .fa-xl { font-size: 32px; }

            /* Bootstrap Icons sizing */
            .bi.icon-xs { font-size: 12px; }
            .bi.icon-sm { font-size: 16px; }
            .bi.icon-md { font-size: 20px; }
            .bi.icon-lg { font-size: 24px; }
            .bi.icon-xl { font-size: 32px; }

            /* SVG icons */
            svg.feather {
                stroke: currentColor;
                fill: none;
                stroke-width: 2;
                stroke-linecap: round;
                stroke-linejoin: round;
            }
        `;
        document.head.appendChild(style);
    }

    function createHeroicon(name, opts) {
        // Common Heroicons SVG paths (outline versions)
        const heroicons = {
            'check': '<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />',
            'x': '<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />',
            'menu': '<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />',
            'home': '<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />',
            'user': '<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />',
            'cog': '<path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />'
        };

        const path = heroicons[name] || '';
        return `<svg class="heroicon ${opts.class}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width: 20px; height: 20px; ${opts.style}">
            ${path}
        </svg>`;
    }

    function createLucideIcon(name, opts) {
        // Common Lucide icon paths
        const lucideIcons = {
            'circle-check': '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
            'alert-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
            'info': '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'
        };

        const path = lucideIcons[name] || '';
        return `<svg class="lucide ${opts.class}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 20px; height: 20px; ${opts.style}">
            ${path}
        </svg>`;
    }

    // Replace custom icon SVG placeholders with actual icons
    function replaceCustomIcons() {
        // Find all icon elements with custom icon names
        document.querySelectorAll('use[href^="#icon-fa-"], use[href^="#icon-mi-"], use[href^="#icon-bi-"]').forEach(use => {
            const href = use.getAttribute('href');
            const iconName = href.replace('#icon-', '');
            const svg = use.closest('svg');

            if (!svg || svg.dataset.customReplaced) return;
            svg.dataset.customReplaced = 'true';

            let replacement;

            // Font Awesome
            if (iconName.startsWith('fa-')) {
                const icon = iconName.replace('fa-', '');
                replacement = document.createElement('i');
                replacement.className = `fas fa-${icon}`;
                replacement.style.fontSize = '20px';
            }
            // Material Icons
            else if (iconName.startsWith('mi-')) {
                const icon = iconName.replace('mi-', '');
                replacement = document.createElement('span');
                replacement.className = 'material-icons';
                replacement.textContent = icon;
                replacement.style.fontSize = '20px';
            }
            // Bootstrap Icons
            else if (iconName.startsWith('bi-')) {
                replacement = document.createElement('i');
                replacement.className = `bi ${iconName}`;
                replacement.style.fontSize = '20px';
            }

            if (replacement && svg.parentNode) {
                // Copy classes from SVG
                if (svg.className.baseVal) {
                    replacement.className += ' ' + svg.className.baseVal;
                }
                svg.parentNode.replaceChild(replacement, svg);
            }
        });
    }

    // Monitor DOM for icon changes
    function startIconReplacementObserver() {
        const observer = new MutationObserver(function(mutations) {
            let shouldReplace = false;
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            // Check if node contains custom icons
                            if (node.querySelector && node.querySelector('use[href^="#icon-fa-"], use[href^="#icon-mi-"], use[href^="#icon-bi-"]')) {
                                shouldReplace = true;
                            }
                        }
                    });
                }
            });
            if (shouldReplace) {
                setTimeout(replaceCustomIcons, 50);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Initial replacement
        replaceCustomIcons();

        console.log('[Right Hire] Icon replacement observer started');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initIconSets();
            setTimeout(startIconReplacementObserver, 1000);
        });
    } else {
        initIconSets();
        setTimeout(startIconReplacementObserver, 1000);
    }
})();
