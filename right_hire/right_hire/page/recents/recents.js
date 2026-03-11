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
			background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
			border-bottom: 1px solid #e5e7eb;
			position: relative;
			overflow: hidden;
			display: flex;
			align-items: center;
			justify-content: center;
		}

		.preview-icon {
			width: 80px;
			height: 80px;
			background: rgba(255, 255, 255, 0.2);
			border-radius: 20px;
			display: flex;
			align-items: center;
			justify-content: center;
			backdrop-filter: blur(10px);
		}

		.preview-icon svg {
			width: 48px;
			height: 48px;
			stroke: white;
			fill: none;
			stroke-width: 2;
		}

		.preview-doctype-text {
			position: absolute;
			bottom: 15px;
			left: 15px;
			color: white;
			font-size: 12px;
			font-weight: 600;
			text-transform: uppercase;
			letter-spacing: 0.5px;
			opacity: 0.9;
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

	const RECENTS_KEY = 'right_hire.recents.v1';

	// Load recent items
	function loadItems() {
		let items = [];
		try {
			items = JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]');
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
					<div class="empty-state-title">No Recent Pages</div>
					<div class="empty-state-text">Visit some forms to see them appear here</div>
				</div>
			`);
			return;
		}

		// Create cards with simple icon previews
		items.forEach((item, index) => {
			const itemHtml = $(`
				<div class="recent-item" data-index="${index}" data-key="${item.key}">
					<button class="recent-item-close" title="Remove">×</button>
					<div class="recent-item-preview">
						<div class="preview-icon">
							<svg viewBox="0 0 24 24">
								<path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
						</div>
						<div class="preview-doctype-text">${item.doctype || 'Document'}</div>
					</div>
					<div class="recent-item-footer">
						<div class="recent-item-title">${item.docname || 'Untitled'}</div>
						<div class="recent-item-badge">RECENT</div>
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
				let recents = JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]');
				recents = recents.filter(x => x.key !== item.key);
				localStorage.setItem(RECENTS_KEY, JSON.stringify(recents));
				itemHtml.fadeOut(300, function() {
					$(this).remove();
					if ($('#recents-grid .recent-item').length === 0) {
						loadItems();
					}
				});
			});

			grid.append(itemHtml);
		});
	}

	// Clear all button
	page.add_action_icon('trash', function() {
		frappe.confirm('Clear all recent pages?', function() {
			localStorage.removeItem(RECENTS_KEY);
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
