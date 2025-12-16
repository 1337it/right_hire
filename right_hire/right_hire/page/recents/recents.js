frappe.pages['recents'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Recent Pages',
		single_column: true
	});

	// Add custom styles
	const style = document.createElement('style');
	style.textContent = `
		.recents-container {
			padding: 20px;
			background: var(--bg-color);
			min-height: calc(100vh - 200px);
		}

		.recents-grid {
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
			gap: 20px;
			margin-top: 20px;
		}

		.recent-item {
			position: relative;
			background: white;
			border: 1px solid #e5e7eb;
			border-radius: 8px;
			overflow: hidden;
			transition: all 0.2s;
			cursor: pointer;
			height: 280px;
			display: flex;
			flex-direction: column;
		}

		.recent-item:hover {
			border-color: #3b82f6;
			box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
			transform: translateY(-2px);
		}

		.recent-item-preview {
			height: 200px;
			background: #f9fafb;
			border-bottom: 1px solid #e5e7eb;
			position: relative;
			overflow: hidden;
		}

		.preview-iframe-container {
			width: 100%;
			height: 100%;
			position: relative;
			background: white;
			overflow: hidden;
		}

		.preview-iframe {
			border: none;
			pointer-events: none;
			position: absolute;
			top: 0;
			left: 0;
			width: 1280px;
			height: 800px;
			transform: scale(0.25);
			transform-origin: 0 0;
			background: white;
		}

		.preview-loading {
			position: absolute;
			top: 50%;
			left: 50%;
			transform: translate(-50%, -50%);
			color: #9ca3af;
			font-size: 13px;
			z-index: 1;
		}

		.preview-loading-spinner {
			width: 32px;
			height: 32px;
			border: 3px solid #e5e7eb;
			border-top-color: #3b82f6;
			border-radius: 50%;
			animation: spin 0.8s linear infinite;
			margin: 0 auto 10px;
		}

		@keyframes spin {
			to { transform: rotate(360deg); }
		}

		.recent-item-close {
			position: absolute;
			top: 8px;
			right: 8px;
			width: 28px;
			height: 28px;
			background: white;
			border: 1px solid #e5e7eb;
			color: #6b7280;
			border-radius: 6px;
			cursor: pointer;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 18px;
			font-weight: 600;
			line-height: 1;
			z-index: 10;
			opacity: 0;
			transition: all 0.2s;
			box-shadow: 0 2px 4px rgba(0,0,0,0.1);
		}

		.recent-item:hover .recent-item-close {
			opacity: 1;
		}

		.recent-item-close:hover {
			background: #fee2e2;
			border-color: #fecaca;
			color: #dc2626;
		}

		.recent-item-footer {
			padding: 15px 20px;
			background: white;
			display: flex;
			align-items: center;
			justify-content: space-between;
		}

		.recent-item-title {
			font-weight: 600;
			font-size: 14px;
			color: #111827;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
			flex: 1;
			margin-right: 10px;
		}

		.recent-item-badge {
			display: inline-flex;
			align-items: center;
			padding: 4px 10px;
			font-size: 11px;
			font-weight: 600;
			border-radius: 12px;
			background: #dbeafe;
			color: #1e40af;
			flex-shrink: 0;
		}

		.empty-state {
			text-align: center;
			padding: 80px 20px;
			color: #6b7280;
			grid-column: 1 / -1;
		}

		.empty-state-icon {
			font-size: 64px;
			margin-bottom: 20px;
			opacity: 0.3;
		}

		.empty-state-icon svg {
			width: 64px;
			height: 64px;
			stroke: currentColor;
			fill: none;
			margin: 0 auto;
		}

		.empty-state-title {
			font-size: 18px;
			font-weight: 600;
			margin-bottom: 8px;
			color: #111827;
		}

		.empty-state-text {
			font-size: 14px;
		}
	`;
	document.head.appendChild(style);

	// Create container
	const container = $(`
		<div class="recents-container">
			<div class="recents-grid" id="recents-grid"></div>
		</div>
	`).appendTo(page.main);

	const MINIMIZED_KEY = 'minidock.tabs.v1';

	// Load minimized items
	function loadItems() {
		let items = [];
		try {
			items = JSON.parse(localStorage.getItem(MINIMIZED_KEY) || '[]');
		} catch(e) {
			items = [];
		}

		const grid = $('#recents-grid');
		grid.empty();

		if (items.length === 0) {
			grid.html(`
				<div class="empty-state">
					<div class="empty-state-icon">
						<svg viewBox="0 0 24 24">
							<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
						</svg>
					</div>
					<div class="empty-state-title">No Minimized Pages</div>
					<div class="empty-state-text">Click the minimize button on any form to see it here</div>
				</div>
			`);
			return;
		}

		// Create cards with iframe previews
		items.forEach((item, index) => {
			const itemHtml = $(`
				<div class="recent-item" data-index="${index}" data-key="${item.key}">
					<button class="recent-item-close" title="Remove">×</button>
					<div class="recent-item-preview">
						<div class="preview-iframe-container">
							<div class="preview-loading">
								<div class="preview-loading-spinner"></div>
								Generating preview...
							</div>
						</div>
					</div>
					<div class="recent-item-footer">
						<div class="recent-item-title">${item.docname || 'Untitled'}</div>
						<div class="recent-item-badge">PINNED</div>
					</div>
				</div>
			`);

			// Click handler - navigate to the page
			itemHtml.on('click', function(e) {
				if (!$(e.target).hasClass('recent-item-close')) {
					frappe.set_route(item.route);
				}
			});

			// Close button handler
			itemHtml.find('.recent-item-close').on('click', function(e) {
				e.stopPropagation();
				let minimized = JSON.parse(localStorage.getItem(MINIMIZED_KEY) || '[]');
				minimized = minimized.filter(x => x.key !== item.key);
				localStorage.setItem(MINIMIZED_KEY, JSON.stringify(minimized));
				itemHtml.fadeOut(300, function() {
					$(this).remove();
					if ($('#recents-grid .recent-item').length === 0) {
						loadItems();
					}
				});
			});

			grid.append(itemHtml);

			// Load preview after a small delay (stagger loading)
			setTimeout(() => {
				loadPreview(item, itemHtml);
			}, index * 200);
		});
	}

	// Load preview for a single item
	function loadPreview(item, itemHtml) {
		const container = itemHtml.find('.preview-iframe-container');

		// Build the direct URL for the document
		const routeParts = item.route || [];
		let previewUrl;

		if (routeParts[0] === 'Form' && routeParts[1] && routeParts[2]) {
			// Direct form URL
			previewUrl = `${window.location.origin}/app/${routeParts[0].toLowerCase()}/${encodeURIComponent(routeParts[1])}/${encodeURIComponent(routeParts[2])}`;
		} else if (routeParts[0] === 'List' && routeParts[1]) {
			// List URL
			previewUrl = `${window.location.origin}/app/${routeParts[0].toLowerCase()}/${encodeURIComponent(routeParts[1])}`;
		} else {
			// Generic route
			previewUrl = `${window.location.origin}/app/${routeParts.join('/')}`;
		}

		console.log('Loading preview:', previewUrl);

		// Create iframe without sandbox restrictions
		const iframe = $('<iframe class="preview-iframe"></iframe>');

		// Set up load handler
		iframe.on('load', function() {
			console.log('Iframe loaded for:', item.docname);
			console.log('Iframe element:', this);
			console.log('Iframe visible:', $(this).is(':visible'));
			console.log('Iframe dimensions:', this.offsetWidth, 'x', this.offsetHeight);
			setTimeout(() => {
				container.find('.preview-loading').fadeOut(300);
			}, 1500);
		});

		// Error handler
		iframe.on('error', function() {
			console.error('Iframe error for:', item.docname);
			container.find('.preview-loading').text('Preview unavailable');
		});

		// Set iframe source directly to the document URL
		iframe.attr('src', previewUrl);

		// Append iframe to container
		container.append(iframe);

		// Fallback: hide loading after timeout
		setTimeout(() => {
			if (container.find('.preview-loading').is(':visible')) {
				container.find('.preview-loading').fadeOut(300);
			}
		}, 6000);
	}

	// Clear all button
	page.add_action_icon('trash', function() {
		frappe.confirm('Clear all minimized pages?', function() {
			localStorage.removeItem(MINIMIZED_KEY);
			loadItems();
		});
	}, 'Clear All');

	// Refresh button
	page.add_action_icon('refresh', loadItems, 'Refresh');

	// Initial load
	loadItems();

	// Reload when page is shown
	$(wrapper).on('show', loadItems);
};
