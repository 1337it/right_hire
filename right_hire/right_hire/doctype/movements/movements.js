// Copyright (c) 2024, Frappe Technologies and contributors
// For license information, please see license.txt

// Helper functions to get direction-specific field names
function get_damage_logs_field(direction) {
	return direction === 'out' ? 'out_vehicle_damage_logs' : 'in_vehicle_damage_logs';
}

function get_condition_checklist_field(direction) {
	return direction === 'out' ? 'out_vehicle_condition_checklist' : 'in_vehicle_condition_checklist';
}

function get_condition_images_field(direction) {
	return direction === 'out' ? 'out_condition_images' : 'in_condition_images';
}

// Setup modal mode when opened from Kanban
function setup_modal_mode(frm) {
	// Add modal-specific styles
	if (!document.getElementById('movement-modal-styles')) {
		$(`<style id="movement-modal-styles">
			body.modal-mode .navbar,
			body.modal-mode #page-workspace,
			body.modal-mode #page-Workspaces,
			body.modal-mode [id^="page-"]:not([id*="Movements"]),
			body.modal-mode .page-head,
			body.modal-mode .layout-side-section,
			body.modal-mode .form-sidebar,
			body.modal-mode footer,
			body.modal-mode .form-footer,
			body.modal-mode .page-actions,
			body.modal-mode .primary-action,
			body.modal-mode .page-sidebar,
			body.modal-mode [data-page-container] > .page-sidebar,
			body.modal-mode .col-lg-2.layout-side-section,
			body.modal-mode #portal-settings-launcher,
			body.modal-mode .page-form.row {
				display: none !important;
			}
			body.modal-mode html,
			body.modal-mode {
				height: 100% !important;
				overflow: auto !important;
				background-color: white;
			}
			body.modal-mode .layout-main-section-wrapper {
				min-width: 0 !important;
				background-color: hsl(0, 0%, 100%) !important;
			}
			body.modal-mode #page-Movements,
			body.modal-mode [data-name="Movements"],
			body.modal-mode [data-page-container="Movements"] {
				width: 100% !important;
				left: 0 !important;
				position: relative !important;
				height: 100% !important;
			}
			body.modal-mode .layout-main-section {
				width: 100% !important;
				max-width: 100% !important;
				height: 100% !important;
			}
			body.modal-mode .layout-main {
				max-width: 100% !important;
				padding: 0 !important;
				height: 100% !important;
			}
			body.modal-mode .container.page-body {
				margin-left: 0 !important;
				margin-top: 0 !important;
				max-width: 100% !important;
				width: 100% !important;
				height: 100% !important;
			}
			body.modal-mode .page-container {
				padding-top: 0 !important;
			}
			body.modal-mode .form-page {
				padding: 15px !important;
				width: 100% !important;
				height: 100% !important;
				max-width: 100% !important;
			}
			body.modal-mode .form-layout {
				max-width: 100% !important;
				width: 100% !important;
			}
		</style>`).appendTo('head');
	}

	// Add modal-mode class to body
	$('body').addClass('modal-mode');

	// Hide workspace and sidebar - note Workspaces with 's'
	$('#page-workspace, #page-Workspaces, [id^="page-"]:not([id*="Movements"]), .page-sidebar, .layout-side-section, .form-sidebar, #portal-settings-launcher').hide();

	// Style movements page container
	$('#page-Movements, [data-name="Movements"], [data-page-container="Movements"]').css({
		'width': '100%',
		'left': '0',
		'position': 'relative',
		'height': '100%'
	});

	// Expand main content area
	$('.layout-main-section').css({
		'width': '100%',
		'max-width': '100%',
		'height': '100%'
	});

	$('.container.page-body').css({
		'margin-left': '0',
		'max-width': '100%',
		'width': '100%',
		'height': '100%'
	});

	// Style form-page full width and height
	$('.form-page').css({
		'padding': '15px',
		'width': '100%',
		'height': '100%',
		'max-width': '100%'
	});

	$('.form-layout').css({
		'max-width': '100%',
		'width': '100%'
	});

	// Hide primary action (save button) - we have our own in the modal footer
	$('.primary-action, .page-actions, .page-head').hide();
}

frappe.ui.form.on('Movements', {
	refresh: function(frm) {
		// Check if opened in Kanban modal mode
		if (window.location.search.includes('modal=1')) {
			setup_modal_mode(frm);
		}

		// Setup conditional field visibility
		toggle_movement_fields(frm);

		// Apply timeline layout CSS
		apply_timeline_layout_css();

		// Auto-collapse sections for better UX
		auto_collapse_sections(frm);

		// Render interactive damage marker
		render_damage_marker(frm);

		// Render fuel level sliders
		render_fuel_slider(frm, 'out');
		render_fuel_slider(frm, 'in');

		// Render quick tags
		render_quick_tags(frm, 'out');
		render_quick_tags(frm, 'in');

		// Lock damage fields based on inspection state
		lock_damage_fields(frm);

		// Add custom button for damage mapping on mobile
		if (frappe.is_mobile() && frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Add Damage Photo'), function() {
				open_damage_mapper(frm);
			}, __('Actions'));
		}

		// Add replacement workflow buttons
		setup_replacement_workflow_buttons(frm);

		// Show linked movements info
		show_linked_movements(frm);
	},

	after_save: function(frm) {
		// Re-apply locking after save
		lock_damage_fields(frm);
	},

	out_fuel_percentage: function(frm) {
		sync_fuel_display(frm, 'out');
	},

	in_fuel_percentage: function(frm) {
		sync_fuel_display(frm, 'in');
	},

	out_fuel_level: function(frm) {
		// Re-render gauge when dropdown changes
		render_fuel_slider(frm, 'out');
	},

	in_fuel_level: function(frm) {
		// Re-render gauge when dropdown changes
		render_fuel_slider(frm, 'in');
	},

	out_mileage: function(frm) {
		calculate_distance(frm);
	},

	in_mileage: function(frm) {
		calculate_distance(frm);
	},

	before_save: function(frm) {
		// Check for damage detection alerts
		check_damage_alerts(frm);
	},

	validate: function(frm) {
		// Final validation before save
		validate_movement_data(frm);
	},

	onload: function(frm) {
		// Set default agreement types filter
		frm.set_query('agreement_type', function() {
			return {
				filters: {
					name: ['in', ['Rental Agreement', 'Lease Contract', 'Lease to Own']]
				}
			};
		});
	},

	movement_type: function(frm) {
		// Toggle field visibility based on movement type
		toggle_movement_fields(frm);
	},

	agreement_type: function(frm) {
		// Clear agreement_no when type changes
		frm.set_value('agreement_no', '');
	},

});

// Toggle field visibility based on movement type
function toggle_movement_fields(frm) {
	if (!frm.doc.movement_type) return;

	const movement_type = frm.doc.movement_type;

	// Define which fields to show for each movement type
	// out_only: true means no "in" details section at all
	const field_visibility = {
		'NRM - Staff Movement': { staff: true, customer: false, driver: false, out_only: false },
		'NRM - Customer Movement': { staff: false, customer: true, driver: false, out_only: false },
		'Staff Car': { staff: true, customer: false, driver: false, out_only: false },
		'Workshop': { staff: false, customer: false, driver: true, out_only: false },
		'Custody': { staff: false, customer: true, driver: false, out_only: false },
		'NRT - Non-Revenue Transfer': { staff: false, customer: false, driver: true, out_only: false },
		'Delivery': { staff: false, customer: true, driver: true, out_only: true },
		'Recovery': { staff: false, customer: true, driver: true, out_only: false },
		'Test Drive': { staff: false, customer: true, driver: true, out_only: false },
		'Showroom': { staff: false, customer: false, driver: true, out_only: false },
		'Replacement - Customer Return': { staff: false, customer: true, driver: true, out_only: false },
		'Replacement - Vehicle Out': { staff: false, customer: true, driver: true, out_only: true },
		'Other': { staff: true, customer: true, driver: true, out_only: false }
	};

	const visibility = field_visibility[movement_type] || { staff: true, customer: true, driver: true, out_only: false };

	// Toggle Out fields
	frm.toggle_display('out_staff', visibility.staff);
	frm.toggle_display('out_customer', visibility.customer);
	frm.toggle_display('out_driver', visibility.driver);

	// Hide/show all "In" related fields and sections based on out_only flag
	const in_fields = [
		'cb_io', 'in_heading', 'in_date_time', 'custom_column_break_1sywl',
		'in_fuel_level', 'in_fuel_gauge_html', 'in_branch', 'in_notes', 'in_quick_tags',
		'custom_column_break_ibo93', 'in_fuel_percentage', 'in_mileage', 'distance_traveled',
		'in_staff', 'in_customer', 'in_driver',
		'in_vehicle_condition_section', 'in_damage_marker_html', 'condition_delta',
		'in_vehicle_damage_logs', 'in_vehicle_condition_checklist', 'in_condition_images'
	];

	if (visibility.out_only) {
		// Hide all "in" fields for out-only movements like Delivery
		in_fields.forEach(field => {
			frm.toggle_display(field, false);
		});
	} else {
		// Show "in" fields (except staff/customer/driver which are controlled separately)
		in_fields.forEach(field => {
			if (!['in_staff', 'in_customer', 'in_driver'].includes(field)) {
				frm.toggle_display(field, true);
			}
		});
		// Toggle In staff/customer/driver fields
		frm.toggle_display('in_staff', visibility.staff);
		frm.toggle_display('in_customer', visibility.customer);
		frm.toggle_display('in_driver', visibility.driver);
	}

	// Clear hidden fields
	if (!visibility.staff) {
		frm.set_value('out_staff', '');
		if (!visibility.out_only) frm.set_value('in_staff', '');
	}
	if (!visibility.customer) {
		frm.set_value('out_customer', '');
		if (!visibility.out_only) frm.set_value('in_customer', '');
	}
	if (!visibility.driver) {
		frm.set_value('out_driver', '');
		if (!visibility.out_only) frm.set_value('in_driver', '');
	}

	frm.refresh_fields();
}

// Open damage mapper for mobile
function open_damage_mapper(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Add Vehicle Damage Photo'),
		fields: [
			{
				fieldname: 'section',
				fieldtype: 'Select',
				label: __('Vehicle Section'),
				options: 'Front\nRear\nLeft Side\nRight Side\nTop\nInterior\nEngine\nTrunk\nOther',
				reqd: 1
			},
			{
				fieldname: 'image_type',
				fieldtype: 'Select',
				label: __('Image Type'),
				options: 'General\nDamage - Front\nDamage - Rear\nDamage - Left Side\nDamage - Right Side\nDamage - Top\nInterior\nOdometer\nOther',
				default: 'General',
				reqd: 1
			},
			{
				fieldname: 'damage_location',
				fieldtype: 'Data',
				label: __('Damage Location'),
				description: __('Specific location of damage')
			},
			{
				fieldname: 'description',
				fieldtype: 'Small Text',
				label: __('Description')
			},
			{
				fieldname: 'canvas_section',
				fieldtype: 'Section Break',
				label: __('Mark Damage on Vehicle')
			},
			{
				fieldname: 'canvas_html',
				fieldtype: 'HTML',
				label: __('Vehicle Silhouette')
			},
			{
				fieldname: 'image_section',
				fieldtype: 'Section Break',
				label: __('Capture Photo')
			},
			{
				fieldname: 'capture_button',
				fieldtype: 'HTML',
				label: __('Capture')
			}
		],
		primary_action_label: __('Save'),
		primary_action(values) {
			// Get damage coordinates from canvas
			const coordinates = get_damage_coordinates();

			// This will be handled by the camera capture button
			// The actual file upload happens through the mobile camera interface
			frappe.msgprint(__('Please use the "Capture Photo" button below to take a picture'));
		}
	});

	// Render vehicle silhouette canvas
	d.fields_dict.canvas_html.$wrapper.html(`
		<div style="position: relative; width: 100%; max-width: 400px; margin: 0 auto; background: #f5f5f5; border-radius: 8px; padding: 20px;">
			<canvas id="vehicle-silhouette" width="360" height="200" style="border: 2px solid #ccc; background: white; border-radius: 4px; cursor: crosshair;"></canvas>
			<p style="margin-top: 10px; font-size: 12px; color: #666;">Tap on the vehicle to mark damage location</p>
		</div>
	`);

	// Render capture button with mobile camera support
	d.fields_dict.capture_button.$wrapper.html(`
		<div style="text-align: center; margin: 20px 0;">
			<input type="file" id="damage-photo-input" accept="image/*" capture="environment" style="display: none;" />
			<button class="btn btn-primary btn-lg" onclick="document.getElementById('damage-photo-input').click();">
				<i class="fa fa-camera"></i> ${__('Take Photo')}
			</button>
		</div>
	`);

	d.show();

	// Draw vehicle silhouette and setup handlers after dialog is shown
	setTimeout(function() {
		draw_vehicle_silhouette();

		// Handle file upload using jQuery for better compatibility
		const photo_input = $('#damage-photo-input');
		if (photo_input.length) {
			photo_input.on('change', function(e) {
				handle_damage_photo_upload(e, frm, d);
			});
		}
	}, 100);
}

// Draw vehicle silhouette on canvas
function draw_vehicle_silhouette() {
	const canvas = document.getElementById('vehicle-silhouette');
	if (!canvas) return;

	const ctx = canvas.getContext('2d');

	// Clear canvas
	ctx.clearRect(0, 0, canvas.width, canvas.height);

	// Draw vehicle outline (top view)
	ctx.strokeStyle = '#333';
	ctx.lineWidth = 2;

	// Main body
	ctx.beginPath();
	ctx.roundRect(80, 40, 200, 120, 10);
	ctx.stroke();

	// Windshield
	ctx.beginPath();
	ctx.moveTo(100, 40);
	ctx.lineTo(120, 50);
	ctx.lineTo(240, 50);
	ctx.lineTo(260, 40);
	ctx.stroke();

	// Rear window
	ctx.beginPath();
	ctx.moveTo(100, 160);
	ctx.lineTo(120, 150);
	ctx.lineTo(240, 150);
	ctx.lineTo(260, 160);
	ctx.stroke();

	// Wheels
	ctx.fillStyle = '#666';
	// Front left wheel
	ctx.fillRect(70, 60, 10, 30);
	// Front right wheel
	ctx.fillRect(280, 60, 10, 30);
	// Rear left wheel
	ctx.fillRect(70, 110, 10, 30);
	// Rear right wheel
	ctx.fillRect(280, 110, 10, 30);

	// Add labels
	ctx.fillStyle = '#999';
	ctx.font = '12px Arial';
	ctx.textAlign = 'center';
	ctx.fillText('FRONT', 180, 30);
	ctx.fillText('REAR', 180, 185);
	ctx.fillText('LEFT', 50, 100);
	ctx.fillText('RIGHT', 310, 100);

	// Handle clicks on canvas to mark damage
	canvas.onclick = function(e) {
		const rect = canvas.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const y = e.clientY - rect.top;

		// Draw damage marker
		ctx.fillStyle = 'red';
		ctx.beginPath();
		ctx.arc(x, y, 5, 0, 2 * Math.PI);
		ctx.fill();

		// Draw X mark
		ctx.strokeStyle = 'red';
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.moveTo(x - 7, y - 7);
		ctx.lineTo(x + 7, y + 7);
		ctx.moveTo(x + 7, y - 7);
		ctx.lineTo(x - 7, y + 7);
		ctx.stroke();

		// Store coordinates
		canvas.dataset.damageX = x;
		canvas.dataset.damageY = y;
	};
}

// Get damage coordinates from canvas
function get_damage_coordinates() {
	const canvas = document.getElementById('vehicle-silhouette');
	if (!canvas) return null;

	return {
		x: canvas.dataset.damageX || 0,
		y: canvas.dataset.damageY || 0,
		width: canvas.width,
		height: canvas.height
	};
}

// Handle damage photo upload
function handle_damage_photo_upload(e, frm, dialog) {
	const file = e.target.files[0];
	if (!file) return;

	// Show loading message
	frappe.show_alert({message: __('Uploading photo...'), indicator: 'blue'});

	// Upload file
	frappe.call({
		method: 'frappe.client.attach_file',
		args: {
			filename: file.name,
			filedata: null,
			doctype: 'Movements',
			docname: frm.doc.name
		},
		callback: function(r) {
			if (r.message) {
				// Get dialog values
				const values = dialog.get_values();
				const coordinates = get_damage_coordinates();

				// Add to condition images based on context
				const images_field = get_condition_images_field(direction);
				let row = frm.add_child(images_field);
				row.image = r.message.file_url;
				row.image_type = values.image_type;
				row.section = values.section;
				row.damage_location = values.damage_location;
				row.description = values.description;
				row.damage_coordinates = JSON.stringify(coordinates);

				frm.refresh_field(images_field);
				frm.save();

				frappe.show_alert({message: __('Photo added successfully'), indicator: 'green'});
				dialog.hide();
			}
		},
		error: function(r) {
			frappe.show_alert({message: __('Failed to upload photo'), indicator: 'red'});
		}
	});

	// Read file as data URL for immediate upload
	const reader = new FileReader();
	reader.onload = function(e) {
		// Extract base64 data from data URL (remove "data:image/...;base64," prefix)
		const base64Data = e.target.result.split(',')[1];

		// Override the filedata argument
		frappe.call({
			method: 'frappe.client.attach_file',
			args: {
				filename: file.name,
				filedata: base64Data,
				doctype: 'Movements',
				docname: frm.doc.name,
				decode_base64: 1
			}
		});
	};
	reader.readAsDataURL(file);
}

// ===== INTERACTIVE DAMAGE MARKER (Phase 2) =====

function render_damage_marker(frm) {
	// Render both OUT and IN sections
	render_damage_marker_section(frm, 'out');
	render_damage_marker_section(frm, 'in');
}

function render_damage_marker_section(frm, direction) {
	// direction is 'out' or 'in'
	const field_name = `${direction}_damage_marker_html`;

	// Get the HTML field wrapper
	if (!frm.fields_dict[field_name]) {
		console.error(`${field_name} field not found in form`);
		return;
	}

	const wrapper = frm.fields_dict[field_name].$wrapper;
	if (!wrapper || !wrapper.length) {
		console.error(`${field_name} wrapper not found`);
		return;
	}

	console.log(`Rendering ${direction} damage marker...`);

	// Clear existing content
	wrapper.empty();

	const title = direction === 'out' ? 'Vehicle Condition at OUT' : 'Vehicle Condition at IN';
	const containerId = `damage-marker-svg-container-${direction}`;

	// Create container with mobile-responsive styling
	const container = $(`
		<div class="damage-marker-container" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;">
			<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
				<h5 style="margin: 0; color: #333;">
					<i class="fa fa-car"></i> ${title}
				</h5>
				<button class="btn btn-sm btn-primary add-damage-btn-${direction}">
					<i class="fa fa-plus"></i> Add Damage
				</button>
			</div>
			<div id="${containerId}" class="svg-damage-container" style="position: relative; margin: 0 auto; border: 2px solid #dee2e6; background: white; border-radius: 4px; overflow: hidden; max-width: 100%;">
				<!-- SVG will be loaded here -->
			</div>
			<p style="margin-top: 10px; font-size: 12px; color: #6c757d; text-align: center;">
				Click on any vehicle part to mark damage locations. Pinch to zoom on mobile.
			</p>
		</div>
	`).appendTo(wrapper);

	// Load and setup SVG - add slight delay to ensure DOM is ready
	setTimeout(() => {
		console.log(`Attempting to load ${direction} SVG...`);
		load_and_setup_svg(frm, direction);
	}, 300);

	// Add damage button handler
	container.find(`.add-damage-btn-${direction}`).on('click', function() {
		add_damage_dialog(frm, direction);
	});
}

// Legacy render function kept for compatibility
function render_damage_marker_legacy(frm) {
	// Get the HTML field wrapper
	if (!frm.fields_dict.damage_marker_html) {
		return;
	}

	const wrapper = frm.fields_dict.damage_marker_html.$wrapper;
	wrapper.empty();
	wrapper.html('<p style="color: #999;">Legacy section - use Out/In sections above</p>');
}

function load_and_setup_svg(frm, direction) {
	direction = direction || 'out'; // Default to 'out'
	const containerId = `damage-marker-svg-container-${direction}`;
	const container = $(`#${containerId}`);

	if (!container.length) {
		console.error(`SVG container ${containerId} not found`);
		return;
	}

	// Show loading message
	container.html('<div style="padding: 40px; text-align: center;"><i class="fa fa-spinner fa-spin"></i> Loading vehicle diagram...</div>');

	// Load the SVG file
	$.ajax({
		url: '/files/car-damage-zones.svg',
		dataType: 'text',
		cache: false,
		success: function(svgContent) {
			console.log(`SVG loaded successfully for ${direction}`);

			// Insert SVG
			container.html(svgContent);

			// Get the SVG element
			const svg = container.find('svg')[0];
			if (!svg) {
				console.error('SVG element not found after loading');
				container.html('<div style="padding: 40px; text-align: center; color: #f44336;">Error: SVG not found in content</div>');
				return;
			}

			// Make SVG responsive and mobile-friendly
			$(svg).css({
				'width': '100%',
				'height': 'auto',
				'display': 'block',
				'touch-action': 'pinch-zoom'
			});

			// Add mobile-responsive styling
			add_mobile_responsive_styles(container);

			// Add markers group to SVG if it doesn't exist
			const markersGroupId = `damage-markers-group-${direction}`;
			let markersGroup = $(svg).find(`#${markersGroupId}`)[0];
			if (!markersGroup) {
				markersGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
				markersGroup.id = markersGroupId;
				svg.appendChild(markersGroup);
			}

			// Setup click handlers for all car parts
			setup_svg_click_handlers(frm, svg, direction);

			// Draw existing damage markers
			draw_svg_damage_markers(frm, svg, direction);

			console.log(`SVG setup complete for ${direction}`);
		},
		error: function(xhr, status, error) {
			console.error('Failed to load SVG:', status, error);
			// Fallback: show error message with more details
			container.html(`
				<div style="padding: 40px; text-align: center; color: #999;">
					<i class="fa fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 10px; color: #ff9800;"></i>
					<p style="font-size: 14px; margin-bottom: 10px;">Unable to load vehicle diagram</p>
					<p style="font-size: 12px; color: #666;">Error: ${status} - ${error}</p>
					<button class="btn btn-sm btn-default" onclick="location.reload();" style="margin-top: 10px;">
						<i class="fa fa-refresh"></i> Refresh Page
					</button>
				</div>
			`);
		}
	});
}

function add_mobile_responsive_styles(container) {
	// Add responsive CSS for mobile devices
	const style = $(`
		<style>
			.svg-damage-container {
				min-height: 300px;
			}

			/* Mobile devices */
			@media (max-width: 768px) {
				.svg-damage-container {
					min-height: 400px;
					max-width: 100% !important;
				}
				.svg-damage-container svg {
					min-width: 100%;
					min-height: 400px;
				}
				.damage-marker-container {
					padding: 10px !important;
				}
			}

			/* Very small screens */
			@media (max-width: 480px) {
				.svg-damage-container {
					min-height: 350px;
				}
				.svg-damage-container svg {
					min-height: 350px;
				}
			}
		</style>
	`);

	if ($('head').find('style.svg-responsive-styles').length === 0) {
		style.addClass('svg-responsive-styles').appendTo('head');
	}
}

function setup_svg_click_handlers(frm, svg, direction) {
	direction = direction || 'out';
	// Get all clickable elements (panels, windows, mirrors, lights, wheels)
	const clickableElements = $(svg).find('.car-panel, .car-window, .car-mirror, .car-light-front, .car-light-rear, .car-tire, .car-rim');

	clickableElements.each(function() {
		$(this).on('click', function(e) {
			if (frm.doc.docstatus !== 0) return; // Only allow in draft

			e.stopPropagation();

			// Get the element ID and map to zone name
			const elementId = this.id;
			const zoneName = map_svg_id_to_zone(elementId);

			// Get click position relative to SVG
			const svgRect = svg.getBoundingClientRect();
			const x = ((e.clientX - svgRect.left) / svgRect.width) * 100;
			const y = ((e.clientY - svgRect.top) / svgRect.height) * 100;

			// Open dialog with auto-detected zone and direction
			open_damage_entry_dialog(frm, x, y, zoneName, direction);
		});

		// Add visual feedback
		$(this).css('cursor', 'crosshair');
	});
}

function map_svg_id_to_zone(elementId) {
	// Map SVG element IDs to Frappe zone names
	const idToZoneMap = {
		'roof_panel': 'Roof',
		'windshield_front': 'Windshield',
		'windshield_rear': 'Rear Window',
		'hood_panel': 'Hood',
		'bumper_front': 'Front Bumper',
		'headlight_left': 'Headlight Left',
		'headlight_right': 'Headlight Right',
		'trunk_panel': 'Trunk/Tailgate',
		'bumper_rear': 'Rear Bumper',
		'taillight_left': 'Taillight Left',
		'taillight_right': 'Taillight Right',
		'fender_front_left': 'Front Left Fender',
		'fender_front_right': 'Front Right Fender',
		'door_front_left': 'Front Left Door',
		'door_front_right': 'Front Right Door',
		'door_rear_left': 'Rear Left Door',
		'door_rear_right': 'Rear Right Door',
		'window_front_left': 'Front Left Window',
		'window_front_right': 'Front Right Window',
		'window_rear_left': 'Rear Left Window',
		'window_rear_right': 'Rear Right Window',
		'quarter_rear_left': 'Rear Left Quarter Panel',
		'quarter_rear_right': 'Rear Right Quarter Panel',
		'mirror_left': 'Front Left Side Mirror',
		'mirror_right': 'Front Right Side Mirror',
		// Wheels (tires)
		'wheel_front_left': 'Front Left Wheel',
		'wheel_front_right': 'Front Right Wheel',
		'wheel_rear_left': 'Rear Left Wheel',
		'wheel_rear_right': 'Rear Right Wheel',
		// Rims (separate zones)
		'rim_front_left': 'Front Left Rim',
		'rim_front_right': 'Front Right Rim',
		'rim_rear_left': 'Rear Left Rim',
		'rim_rear_right': 'Rear Right Rim'
	};

	return idToZoneMap[elementId] || 'Other';
}

function draw_svg_damage_markers(frm, svg, direction) {
	direction = direction || 'out';
	// Get the markers group for this direction
	const markersGroupId = `damage-markers-group-${direction}`;
	let markersGroup = $(svg).find(`#${markersGroupId}`)[0];
	if (!markersGroup) return;

	// Clear existing markers
	$(markersGroup).empty();

	// Get damage logs based on direction
	const damage_field = get_damage_logs_field(direction);
	const damages = frm.doc[damage_field] || [];

	damages.forEach((damage, index) => {
		if (damage.x_coordinate && damage.y_coordinate) {
			// Calculate position (x, y are percentages 0-100)
			// SVG viewBox is 660x680
			const x = damage.x_coordinate * 6.6; // Convert percentage to SVG coordinates (660/100)
			const y = damage.y_coordinate * 6.8; // Convert percentage to SVG coordinates (680/100)

			// Get damage state color
			const color = get_damage_state_color(damage);

			// Create marker circle
			const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
			circle.setAttribute('cx', x);
			circle.setAttribute('cy', y);
			circle.setAttribute('r', 18);
			circle.setAttribute('fill', color);
			circle.setAttribute('stroke', 'white');
			circle.setAttribute('stroke-width', 3);
			circle.setAttribute('class', 'damage-marker');
			circle.setAttribute('data-index', index);
			circle.style.cursor = 'pointer';

			// Add number text
			const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
			text.setAttribute('x', x);
			text.setAttribute('y', y);
			text.setAttribute('fill', 'white');
			text.setAttribute('font-size', '14');
			text.setAttribute('font-weight', 'bold');
			text.setAttribute('text-anchor', 'middle');
			text.setAttribute('dominant-baseline', 'middle');
			text.setAttribute('class', 'damage-marker-text');
			text.setAttribute('data-index', index);
			// Ensure item_number starts from 1 (use index + 1 if item_number is not set or is 0)
			text.textContent = (damage.item_number && damage.item_number > 0) ? damage.item_number : (index + 1);
			text.style.pointerEvents = 'none';

			// Add click handler to marker
			$(circle).on('click', function(e) {
				e.stopPropagation();
				const idx = parseInt($(this).attr('data-index'));
				const damage_field = get_damage_logs_field(direction);
			const damages = frm.doc[damage_field] || [];
				if (damages[idx]) {
					open_damage_details_dialog(frm, damages[idx], idx);
				}
			});

			markersGroup.appendChild(circle);
			markersGroup.appendChild(text);
		}
	});
}

// Old canvas functions removed - now using SVG directly

function get_damage_state_color(damage) {
	// Color coding based on damage state:
	// Green = existing damage (marked during OUT)
	// Yellow = worsened damage (severity increased from OUT to IN)
	// Red = new damage (found during IN)

	const state = damage.damage_state || 'new';

	const colors = {
		'existing': '#4caf50',    // Green - damage was already there
		'worsened': '#ffc107',    // Yellow - severity increased
		'new': '#f44336'          // Red - new damage found
	};

	return colors[state] || '#f44336'; // Default to red (new)
}

function get_severity_color(severity) {
	const colors = {
		'Minor': '#ffc107',      // Yellow
		'Moderate': '#ff9800',   // Orange
		'Severe': '#f44336',     // Red
		'Critical': '#c62828'    // Dark Red
	};
	return colors[severity] || '#2196f3'; // Default blue
}

// Old canvas-based zone detection removed - now using SVG element IDs directly

function open_damage_details_dialog(frm, damage, index, direction) {
	// Check if user can edit - only admins can edit after damage is created
	const can_edit = frappe.user.has_role('System Manager') || frappe.user.has_role('Administrator');

	const d = new frappe.ui.Dialog({
		title: __('Damage #{0} Details', [damage.item_number || (index + 1)]),
		fields: [
			{
				fieldname: 'zone',
				fieldtype: 'Select',
				label: __('Zone'),
				options: 'Front Bumper\nRear Bumper\nFront Left Door\nFront Right Door\nRear Left Door\nRear Right Door\nFront Left Fender\nFront Right Fender\nRear Left Quarter Panel\nRear Right Quarter Panel\nHood\nRoof\nTrunk/Tailgate\nFront Left Wheel\nFront Right Wheel\nRear Left Wheel\nRear Right Wheel\nFront Left Rim\nFront Right Rim\nRear Left Rim\nRear Right Rim\nWindshield\nRear Window\nFront Left Window\nFront Right Window\nRear Left Window\nRear Right Window\nFront Left Side Mirror\nFront Right Side Mirror\nHeadlight Left\nHeadlight Right\nTaillight Left\nTaillight Right\nGrille\nUndercarriage\nInterior\nOther',
				default: damage.zone,
				read_only: !can_edit
			},
			{
				fieldname: 'damage_type',
				fieldtype: 'Select',
				label: __('Damage Type'),
				options: 'Scratch\nDent\nPaint Chip\nCrack\nBroken\nMissing Part\nRust\nScuff\nTear\nStain\nBurn\nOther',
				default: damage.damage_type,
				read_only: !can_edit
			},
			{
				fieldname: 'col_break',
				fieldtype: 'Column Break'
			},
			{
				fieldname: 'severity',
				fieldtype: 'Select',
				label: __('Severity'),
				options: 'Minor\nModerate\nSevere\nCritical',
				default: damage.severity,
				read_only: !can_edit
			},
			{
				fieldname: 'damage_state',
				fieldtype: 'Data',
				label: __('Damage State'),
				default: damage.damage_state || 'new',
				description: __('Green=existing, Yellow=worsened, Red=new (Auto-detected)'),
				read_only: 1
			},
			{
				fieldname: 'sec_break',
				fieldtype: 'Section Break',
				label: __('Details')
			},
			{
				fieldname: 'description',
				fieldtype: 'Small Text',
				label: __('Description'),
				default: damage.description,
				read_only: !can_edit
			},
			{
				fieldname: 'images_section',
				fieldtype: 'Section Break',
				label: __('Damage Images')
			},
			{
				fieldname: 'images_html',
				fieldtype: 'HTML',
				options: render_damage_images_html(damage, can_edit)
			}
		],
		primary_action_label: can_edit ? __('Update Damage') : __('Close'),
		primary_action(values) {
			if (can_edit) {
				// Update the damage log
				const damage_field = get_damage_logs_field(direction);
			const damages = frm.doc[damage_field] || [];
				if (damages[index]) {
					damages[index].zone = values.zone;
					damages[index].damage_type = values.damage_type;
					damages[index].severity = values.severity;
					damages[index].damage_state = values.damage_state;
					damages[index].description = values.description;

					frm.refresh_field(damage_field);

					// Redraw SVG markers
					const svg = $(`#damage-marker-svg-container-${direction} svg`)[0];
					if (svg) {
						draw_svg_damage_markers(frm, svg, direction);
					}

					frappe.show_alert({
						message: __('Damage updated'),
						indicator: 'green'
					});
				}
			}
			d.hide();
		}
	});

	if (!can_edit) {
		d.set_secondary_action_label(__('Admin Only'));
		d.set_secondary_action(() => {
			frappe.msgprint({
				title: __('Permission Denied'),
				message: __('Only administrators can edit damages after they have been created.'),
				indicator: 'orange'
			});
		});
	}

	d.show();

	// Set up image upload handler after dialog is shown
	if (can_edit) {
		setTimeout(() => {
			const upload_input = d.$wrapper.find('#damage-image-upload');
			const upload_btn = d.$wrapper.find('.add-damage-image-btn');

			if (upload_input.length && upload_btn.length) {
				// Connect button to file input
				upload_btn.off('click').on('click', function() {
					upload_input.click();
				});

				// Handle file selection
				upload_input.off('change').on('change', function(e) {
					handle_multiple_damage_images_upload(e, frm, damage, d);
				});
			}
		}, 200);
	}
}

function handle_multiple_damage_images_upload(e, frm, damage, dialog) {
	const files = Array.from(e.target.files);
	if (files.length === 0) return;

	frappe.show_alert({
		message: __('Uploading {0} image(s)...', [files.length]),
		indicator: 'blue'
	});

	let uploaded = 0;
	let failed = 0;

	files.forEach((file, index) => {
		const reader = new FileReader();
		reader.onload = function(event) {
			// Extract base64 data from data URL
			const base64Data = event.target.result.split(',')[1];

			frappe.call({
				method: 'frappe.client.attach_file',
				args: {
					filename: file.name,
					filedata: base64Data,
					doctype: 'Movements',
					docname: frm.doc.name,
					decode_base64: 1
				},
				callback: function(r) {
					if (r.message) {
						uploaded++;

						// Add to damage_images child table
						if (!damage.damage_images) {
							damage.damage_images = [];
						}

						damage.damage_images.push({
							image: r.message.file_url,
							caption: file.name
						});

						// Check if all files are processed
						if (uploaded + failed === files.length) {
							frm.refresh_field(damage_field);
							frm.save();

							frappe.show_alert({
								message: __('Successfully uploaded {0} image(s)', [uploaded]),
								indicator: 'green'
							});

							dialog.hide();

							// Reopen dialog to show new images
							setTimeout(() => {
								const damage_field = get_damage_logs_field(direction);
			const damages = frm.doc[damage_field] || [];
								const damage_index = damages.findIndex(d => d.item_number === damage.item_number);
								if (damage_index >= 0) {
									open_damage_details_dialog(frm, damages[damage_index], damage_index);
								}
							}, 500);
						}
					} else {
						failed++;
						if (uploaded + failed === files.length) {
							frappe.msgprint({
								title: __('Upload Complete'),
								message: __('Uploaded: {0}, Failed: {1}', [uploaded, failed]),
								indicator: failed > 0 ? 'orange' : 'green'
							});
						}
					}
				},
				error: function() {
					failed++;
					if (uploaded + failed === files.length) {
						frappe.msgprint({
							title: __('Upload Complete'),
							message: __('Uploaded: {0}, Failed: {1}', [uploaded, failed]),
							indicator: 'orange'
						});
					}
				}
			});
		};
		reader.readAsDataURL(file);
	});

	// Reset input
	e.target.value = '';
}

function render_damage_images_html(damage, can_edit) {
	const images = damage.damage_images || [];
	let html = `<div class="damage-images-container" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px;">`;

	images.forEach((img, idx) => {
		html += `
			<div class="damage-image-item" style="position: relative; border: 1px solid #ddd; border-radius: 4px; overflow: hidden;">
				<img src="${img.image}" style="width: 100%; height: 150px; object-fit: cover; cursor: pointer;" onclick="window.open('${img.image}', '_blank')" />
				${img.caption ? `<div style="padding: 5px; font-size: 11px; background: #f5f5f5;">${img.caption}</div>` : ''}
			</div>
		`;
	});

	if (images.length === 0) {
		html += '<p style="color: #999; font-style: italic; grid-column: 1/-1;">No images attached</p>';
	}

	html += '</div>';

	if (can_edit) {
		html += `
			<div style="margin-top: 15px;">
				<input type="file" id="damage-image-upload" accept="image/*" multiple style="display: none;" />
				<button class="btn btn-sm btn-primary add-damage-image-btn">
					<i class="fa fa-camera"></i> Add Images (Multiple)
				</button>
				<p style="margin-top: 5px; font-size: 11px; color: #666;">You can select multiple images at once</p>
			</div>
		`;
	}

	return html;
}

function open_damage_entry_dialog(frm, x_coord, y_coord, auto_zone, direction) {
	direction = direction || 'out'; // Default to 'out'
	const d = new frappe.ui.Dialog({
		title: __('Add Damage Entry'),
		fields: [
			{
				fieldname: 'zone',
				fieldtype: 'Select',
				label: __('Zone'),
				options: 'Front Bumper\nRear Bumper\nFront Left Door\nFront Right Door\nRear Left Door\nRear Right Door\nFront Left Fender\nFront Right Fender\nRear Left Quarter Panel\nRear Right Quarter Panel\nHood\nRoof\nTrunk/Tailgate\nFront Left Wheel\nFront Right Wheel\nRear Left Wheel\nRear Right Wheel\nFront Left Rim\nFront Right Rim\nRear Left Rim\nRear Right Rim\nWindshield\nRear Window\nFront Left Window\nFront Right Window\nRear Left Window\nRear Right Window\nFront Left Side Mirror\nFront Right Side Mirror\nHeadlight Left\nHeadlight Right\nTaillight Left\nTaillight Right\nGrille\nUndercarriage\nInterior\nOther',
				default: auto_zone,
				reqd: 1
			},
			{
				fieldname: 'damage_type',
				fieldtype: 'Select',
				label: __('Damage Type'),
				options: 'Scratch\nDent\nPaint Chip\nCrack\nBroken\nMissing Part\nRust\nScuff\nTear\nStain\nBurn\nOther',
				reqd: 1
			},
			{
				fieldname: 'col_break',
				fieldtype: 'Column Break'
			},
			{
				fieldname: 'severity',
				fieldtype: 'Select',
				label: __('Severity'),
				options: 'Minor\nModerate\nSevere\nCritical',
				default: 'Minor'
			},
			{
				fieldname: 'sec_break',
				fieldtype: 'Section Break',
				label: __('Details')
			},
			{
				fieldname: 'description',
				fieldtype: 'Small Text',
				label: __('Description')
			},
			{
				fieldname: 'images_section',
				fieldtype: 'Section Break',
				label: __('Photo Evidence')
			},
			{
				fieldname: 'image_upload_html',
				fieldtype: 'HTML',
				label: __('Upload Images')
			}
		],
		primary_action_label: __('Add Damage'),
		primary_action(values) {
			// Get next item number
			const damage_field = get_damage_logs_field(direction);
			const damages = frm.doc[damage_field] || [];
			const next_item_number = damages.length + 1;

			// Add damage log
			const row = frm.add_child(damage_field);
			row.item_number = next_item_number;
			row.zone = values.zone;
			row.damage_type = values.damage_type;
			row.severity = values.severity;
			row.description = values.description;
			row.x_coordinate = x_coord;
			row.y_coordinate = y_coord;

			// Handle uploaded images
			const uploaded_files = d.uploaded_files || [];
			uploaded_files.forEach(file_url => {
				const image_row = frappe.model.add_child(row, 'damage_images');
				image_row.image = file_url;
			});

			frm.refresh_field(damage_field);

			// Update damage state in real-time if this is an IN damage
			if (direction === 'in') {
				update_damage_state_realtime(frm, row.doctype, row.name);
			}

			// Redraw SVG markers
			const svg = $(`#damage-marker-svg-container-${direction} svg`)[0];
			if (svg) {
				draw_svg_damage_markers(frm, svg, direction);
			}

			// Don't show the "Damage added" alert if state detection already showed one
			if (direction !== 'in') {
				frappe.show_alert({
					message: __('Damage #{0} added', [next_item_number]),
					indicator: 'green'
				});
			}

			d.hide();
		}
	});

	if (auto_zone) {
		d.set_value('zone', auto_zone);
	}

	d.show();

	// Add image upload functionality after dialog is shown
	setTimeout(() => {
		const upload_wrapper = d.fields_dict.image_upload_html.$wrapper;
		d.uploaded_files = [];

		const upload_html = `
			<div style="padding: 10px;">
				<input type="file" id="damage-image-upload" multiple accept="image/*" style="display: none;" />
				<button class="btn btn-default btn-sm upload-trigger-btn">
					<i class="fa fa-camera"></i> ${__('Upload Images')}
				</button>
				<div id="damage-images-preview" style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 10px;">
				</div>
			</div>
		`;

		upload_wrapper.html(upload_html);

		// Handle button click to trigger file input
		upload_wrapper.find('.upload-trigger-btn').on('click', function() {
			upload_wrapper.find('#damage-image-upload').click();
		});

		// Handle file selection using jQuery for better compatibility
		upload_wrapper.find('#damage-image-upload').on('change', function(e) {
			const files = Array.from(e.target.files);
			const preview_div = upload_wrapper.find('#damage-images-preview')[0];

			files.forEach((file, index) => {
				const reader = new FileReader();
				reader.onload = function(event) {
					// Extract base64 data from data URL
					const base64Data = event.target.result.split(',')[1];

					// Upload file to server
					frappe.call({
						method: 'frappe.client.attach_file',
						args: {
							filename: file.name,
							filedata: base64Data,
							doctype: 'Movements',
							docname: frm.doc.name,
							decode_base64: 1
						},
						callback: function(r) {
							if (r.message) {
								d.uploaded_files.push(r.message.file_url);

								// Add preview
								const img_preview = $(`
									<div style="position: relative; width: 80px; height: 80px;">
										<img src="${r.message.file_url}" style="width: 100%; height: 100%; object-fit: cover; border: 1px solid #ddd; border-radius: 4px;" />
										<button class="btn btn-xs btn-danger" style="position: absolute; top: 2px; right: 2px; padding: 2px 6px;" data-file="${r.message.file_url}">
											<i class="fa fa-times"></i>
										</button>
									</div>
								`);

								// Handle image removal
								img_preview.find('button').on('click', function() {
									const file_url = $(this).data('file');
									const index = d.uploaded_files.indexOf(file_url);
									if (index > -1) {
										d.uploaded_files.splice(index, 1);
									}
									$(this).parent().remove();
								});

								preview_div.append(img_preview[0]);
							}
						}
					});
				};
				reader.readAsDataURL(file);
			});

			// Clear file input for next selection
			e.target.value = '';
		});
	}, 100);
}

function add_damage_dialog(frm) {
	// Open dialog without coordinates (manual entry)
	open_damage_entry_dialog(frm, null, null);
}

// Listen to damage log changes - Combined handlers for both OUT and IN sections
frappe.ui.form.on('Vehicle Damage Log', {
	// OUT section handlers
	out_vehicle_damage_logs_add: function(frm, cdt, cdn) {
		setTimeout(() => {
			frm.save();
		}, 500);
	},

	out_vehicle_damage_logs_remove: function(frm) {
		// Renumber items
		renumber_damage_items(frm, 'out');
		// Redraw SVG markers
		const svg = $('#damage-marker-svg-container-out svg')[0];
		if (svg) {
			draw_svg_damage_markers(frm, svg, 'out');
		}
	},

	before_out_vehicle_damage_logs_remove: function(frm, cdt, cdn) {
		// Check if user can delete - only admins
		const can_edit = frappe.user.has_role('System Manager') || frappe.user.has_role('Administrator');
		if (!can_edit) {
			frappe.msgprint({
				title: __('Permission Denied'),
				message: __('Only administrators can delete damage logs after creation.'),
				indicator: 'red'
			});
			frappe.validated = false;
			return false;
		}
	},

	// IN section handlers
	in_vehicle_damage_logs_add: function(frm, cdt, cdn) {
		// Update damage state in real-time
		update_damage_state_realtime(frm, cdt, cdn);

		setTimeout(() => {
			frm.save();
		}, 500);
	},

	in_vehicle_damage_logs_remove: function(frm) {
		// Renumber items
		renumber_damage_items(frm, 'in');
		// Redraw SVG markers
		const svg = $('#damage-marker-svg-container-in svg')[0];
		if (svg) {
			draw_svg_damage_markers(frm, svg, 'in');
		}
	},

	before_in_vehicle_damage_logs_remove: function(frm, cdt, cdn) {
		// Check if user can delete - only admins
		const can_edit = frappe.user.has_role('System Manager') || frappe.user.has_role('Administrator');
		if (!can_edit) {
			frappe.msgprint({
				title: __('Permission Denied'),
				message: __('Only administrators can delete damage logs after creation.'),
				indicator: 'red'
			});
			frappe.validated = false;
			return false;
		}
	},

	// Field change handlers (apply to both OUT and IN)
	zone: function(frm, cdt, cdn) {
		check_damage_edit_permission(frm, cdt, cdn);

		// Update damage state for IN damages when zone changes
		const row = locals[cdt][cdn];
		if (row.parentfield === 'in_vehicle_damage_logs') {
			update_damage_state_realtime(frm, cdt, cdn);
		}
	},

	damage_type: function(frm, cdt, cdn) {
		check_damage_edit_permission(frm, cdt, cdn);

		// Update damage state for IN damages when damage_type changes
		const row = locals[cdt][cdn];
		if (row.parentfield === 'in_vehicle_damage_logs') {
			update_damage_state_realtime(frm, cdt, cdn);
		}
	},

	severity: function(frm, cdt, cdn) {
		check_damage_edit_permission(frm, cdt, cdn);

		// Show alert for high severity
		const row = locals[cdt][cdn];
		if (row.severity === 'Critical' || row.severity === 'Severe') {
			frappe.show_alert({
				message: __('High severity damage detected: {0}', [row.severity]),
				indicator: row.severity === 'Critical' ? 'red' : 'orange'
			}, 5);
		}

		// Update damage state for IN damages when severity changes
		if (row.parentfield === 'in_vehicle_damage_logs') {
			update_damage_state_realtime(frm, cdt, cdn);
		}
	}
});

function check_damage_edit_permission(frm, cdt, cdn) {
	// Check if the damage log is saved (not new)
	const row = locals[cdt][cdn];
	if (row && row.name && !row.__islocal) {
		// This is an existing saved damage log
		const can_edit = frappe.user.has_role('System Manager') || frappe.user.has_role('Administrator');
		if (!can_edit) {
			frappe.show_alert({
				message: __('Only administrators can edit saved damage logs'),
				indicator: 'orange'
			}, 5);

			// Optionally, we could prevent the edit but it's better to just warn
		}
	}
}

function update_damage_state_realtime(frm, cdt, cdn) {
	// Real-time damage state detection for IN damages
	const in_damage = locals[cdt][cdn];

	// Only process IN damages
	if (in_damage.parentfield !== 'in_vehicle_damage_logs') {
		return;
	}

	// Map severity to numeric values for comparison
	const severity_map = {
		'Minor': 1,
		'Moderate': 2,
		'Severe': 3,
		'Critical': 4
	};

	// Get OUT damages from this movement
	const out_damages = frm.doc.out_vehicle_damage_logs || [];
	let damage_state = 'new'; // Default to new

	// Look for matching damage in OUT inspection
	for (let out_damage of out_damages) {
		if (in_damage.zone === out_damage.zone &&
		    in_damage.damage_type === out_damage.damage_type) {

			// Found matching damage - check severity
			const in_severity = severity_map[in_damage.severity] || 1;
			const out_severity = severity_map[out_damage.severity] || 1;

			if (in_severity > out_severity) {
				damage_state = 'worsened';
			} else {
				damage_state = 'existing';
			}
			break;
		}
	}

	// Update the damage state field
	frappe.model.set_value(cdt, cdn, 'damage_state', damage_state);

	// Show visual feedback
	if (damage_state === 'existing') {
		frappe.show_alert({
			message: __('✓ Damage already existed at checkout'),
			indicator: 'green'
		}, 2);
	} else if (damage_state === 'worsened') {
		frappe.show_alert({
			message: __('⚠ Damage severity increased during trip'),
			indicator: 'orange'
		}, 2);
	} else {
		frappe.show_alert({
			message: __('🔴 New damage detected'),
			indicator: 'red'
		}, 2);
	}
}

function renumber_damage_items(frm, direction) {
	const damage_field = get_damage_logs_field(direction);
	const damages = frm.doc[damage_field] || [];
	damages.forEach((damage, index) => {
		damage.item_number = index + 1;
	});
	frm.refresh_field(damage_field);
}

function lock_damage_fields(frm) {
	/**
	 * Lock damage fields based on inspection completion:
	 * - IN damages: Lock after they are saved (document saved with IN damages)
	 * - OUT damages: Lock after IN damages are added and saved (full cycle complete)
	 * - IN condition checklist: Lock after saved with data
	 * - OUT condition checklist: Lock after IN inspection is complete
	 * - Administrators can always edit (System Manager or Administrator role)
	 */

	// Check if user is admin - admins can always edit
	const is_admin = frappe.user.has_role('System Manager') || frappe.user.has_role('Administrator');

	// Don't lock anything if document is not saved yet OR user is admin
	if (frm.doc.__islocal || is_admin) {
		frm.set_df_property('in_vehicle_damage_logs', 'read_only', 0);
		frm.set_df_property('out_vehicle_damage_logs', 'read_only', 0);
		frm.set_df_property('in_vehicle_condition_checklist', 'read_only', 0);
		frm.set_df_property('out_vehicle_condition_checklist', 'read_only', 0);
		frm.set_df_property('in_condition_images', 'read_only', 0);
		frm.set_df_property('out_condition_images', 'read_only', 0);
		return;
	}

	// Check if IN damages exist (saved)
	const has_in_damages = (frm.doc.in_vehicle_damage_logs || []).length > 0;
	const has_in_checklist = (frm.doc.in_vehicle_condition_checklist || []).length > 0;
	const has_in_images = (frm.doc.in_condition_images || []).length > 0;

	// IN inspection is complete if any IN data exists and doc is saved
	const in_inspection_complete = has_in_damages || has_in_checklist || has_in_images;

	// Lock IN damage fields after they are saved
	if (in_inspection_complete) {
		frm.set_df_property('in_vehicle_damage_logs', 'read_only', 1);
		frm.set_df_property('in_vehicle_condition_checklist', 'read_only', 1);
		frm.set_df_property('in_condition_images', 'read_only', 1);

		// Also lock OUT damage fields (full inspection cycle is complete)
		frm.set_df_property('out_vehicle_damage_logs', 'read_only', 1);
		frm.set_df_property('out_vehicle_condition_checklist', 'read_only', 1);
		frm.set_df_property('out_condition_images', 'read_only', 1);

		// Show a message to indicate fields are locked (only once per page load)
		if (!frm.__lock_message_shown) {
			frappe.show_alert({
				message: __('🔒 Vehicle condition records are locked after IN inspection is completed'),
				indicator: 'blue'
			}, 5);
			frm.__lock_message_shown = true;
		}
	} else {
		// If IN inspection not done yet, keep everything editable
		frm.set_df_property('in_vehicle_damage_logs', 'read_only', 0);
		frm.set_df_property('out_vehicle_damage_logs', 'read_only', 0);
		frm.set_df_property('in_vehicle_condition_checklist', 'read_only', 0);
		frm.set_df_property('out_vehicle_condition_checklist', 'read_only', 0);
		frm.set_df_property('in_condition_images', 'read_only', 0);
		frm.set_df_property('out_condition_images', 'read_only', 0);
	}
}

// ===== VISUAL FUEL LEVEL SLIDER (Phase 2) =====

function render_fuel_slider(frm, direction) {
	// Get the HTML wrapper for the fuel gauge
	const html_field = `${direction}_fuel_gauge_html`;
	const wrapper = frm.fields_dict[html_field]?.$wrapper;
	if (!wrapper) return;

	wrapper.empty();

	// Get current value from dropdown
	const select_field = `${direction}_fuel_level`;
	const current_level = frm.doc[select_field] || '';

	// Map level to slider position (0-8)
	const level_map = {'': 0, '1/8': 1, '2/8': 2, '3/8': 3, '4/8': 4, '5/8': 5, '6/8': 6, '7/8': 7, '8/8': 8};
	const current_position = level_map[current_level] || 0;

	// Add styles if not present
	if (!document.getElementById('fuel-gauge-styles')) {
		$(`<style id="fuel-gauge-styles">
			.fuel-gauge-wrapper {
				padding: 10px 0;
			}
			.fuel-gauge-container {
				background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
				border-radius: 12px;
				padding: 20px;
				position: relative;
				box-shadow: inset 0 2px 10px rgba(0,0,0,0.3);
			}
			.fuel-gauge-bar {
				height: 40px;
				background: #2d2d44;
				border-radius: 8px;
				position: relative;
				overflow: hidden;
				border: 2px solid #3d3d5c;
			}
			.fuel-gauge-fill {
				height: 100%;
				border-radius: 6px;
				transition: width 0.3s ease, background 0.3s ease;
				position: relative;
			}
			.fuel-gauge-fill.level-low {
				background: linear-gradient(90deg, #ff4444 0%, #ff6b6b 100%);
			}
			.fuel-gauge-fill.level-medium {
				background: linear-gradient(90deg, #ff9800 0%, #ffc107 100%);
			}
			.fuel-gauge-fill.level-high {
				background: linear-gradient(90deg, #4caf50 0%, #8bc34a 100%);
			}
			.fuel-gauge-markers {
				display: flex;
				justify-content: space-between;
				margin-top: 8px;
				padding: 0 2px;
			}
			.fuel-gauge-marker {
				text-align: center;
				cursor: pointer;
				padding: 4px 2px;
				border-radius: 4px;
				transition: background 0.2s;
				min-width: 28px;
			}
			.fuel-gauge-marker:hover {
				background: rgba(255,255,255,0.1);
			}
			.fuel-gauge-marker.active {
				background: rgba(76, 175, 80, 0.3);
			}
			.fuel-gauge-marker .tick {
				width: 2px;
				height: 8px;
				background: #666;
				margin: 0 auto 4px;
			}
			.fuel-gauge-marker .label {
				font-size: 10px;
				color: #aaa;
			}
			.fuel-gauge-marker.active .label {
				color: #4caf50;
				font-weight: bold;
			}
			.fuel-gauge-slider {
				width: 100%;
				margin-top: 15px;
				-webkit-appearance: none;
				height: 8px;
				background: #2d2d44;
				border-radius: 4px;
				outline: none;
			}
			.fuel-gauge-slider::-webkit-slider-thumb {
				-webkit-appearance: none;
				width: 24px;
				height: 24px;
				background: linear-gradient(135deg, #4caf50, #8bc34a);
				border-radius: 50%;
				cursor: pointer;
				border: 3px solid #fff;
				box-shadow: 0 2px 6px rgba(0,0,0,0.3);
			}
			.fuel-gauge-slider::-moz-range-thumb {
				width: 24px;
				height: 24px;
				background: linear-gradient(135deg, #4caf50, #8bc34a);
				border-radius: 50%;
				cursor: pointer;
				border: 3px solid #fff;
				box-shadow: 0 2px 6px rgba(0,0,0,0.3);
			}
			.fuel-gauge-value {
				text-align: center;
				margin-top: 10px;
				font-size: 18px;
				font-weight: bold;
				color: #fff;
			}
			.fuel-gauge-icon {
				position: absolute;
				right: 15px;
				top: 50%;
				transform: translateY(-50%);
				font-size: 20px;
				opacity: 0.7;
			}
		</style>`).appendTo('head');
	}

	const markers = ['E', '1/8', '2/8', '3/8', '4/8', '5/8', '6/8', '7/8', 'F'];

	const gauge_html = $(`
		<div class="fuel-gauge-wrapper">
			<div class="fuel-gauge-container">
				<div class="fuel-gauge-bar">
					<div class="fuel-gauge-fill" style="width: ${(current_position / 8) * 100}%"></div>
					<span class="fuel-gauge-icon">⛽</span>
				</div>
				<div class="fuel-gauge-markers">
					${markers.map((label, idx) => `
						<div class="fuel-gauge-marker ${idx === current_position ? 'active' : ''}" data-level="${idx}">
							<div class="tick"></div>
							<div class="label">${label}</div>
						</div>
					`).join('')}
				</div>
				<input type="range" class="fuel-gauge-slider" min="0" max="8" step="1" value="${current_position}">
				<div class="fuel-gauge-value">${current_level || 'Empty'}</div>
			</div>
		</div>
	`);

	wrapper.append(gauge_html);

	// Update gauge fill color based on level
	function updateGaugeFill(level) {
		const fill = gauge_html.find('.fuel-gauge-fill');
		fill.removeClass('level-low level-medium level-high');
		if (level <= 2) {
			fill.addClass('level-low');
		} else if (level <= 5) {
			fill.addClass('level-medium');
		} else {
			fill.addClass('level-high');
		}
		fill.css('width', `${(level / 8) * 100}%`);
	}

	// Update markers
	function updateMarkers(level) {
		gauge_html.find('.fuel-gauge-marker').removeClass('active');
		gauge_html.find(`.fuel-gauge-marker[data-level="${level}"]`).addClass('active');
	}

	// Update value display
	function updateValue(level) {
		const labels = ['Empty', '1/8', '2/8', '3/8', '4/8', '5/8', '6/8', '7/8', '8/8'];
		gauge_html.find('.fuel-gauge-value').text(labels[level]);
	}

	// Set the dropdown value
	function setFuelLevel(level) {
		const values = ['', '1/8', '2/8', '3/8', '4/8', '5/8', '6/8', '7/8', '8/8'];
		frm.set_value(select_field, values[level]);
		// Also update percentage (level * 12.5)
		frm.set_value(`${direction}_fuel_percentage`, Math.round(level * 12.5));
	}

	// Initial update
	updateGaugeFill(current_position);

	// Handle marker clicks
	gauge_html.find('.fuel-gauge-marker').on('click', function() {
		const level = parseInt($(this).data('level'));
		gauge_html.find('.fuel-gauge-slider').val(level);
		updateGaugeFill(level);
		updateMarkers(level);
		updateValue(level);
		setFuelLevel(level);
	});

	// Handle slider change
	gauge_html.find('.fuel-gauge-slider').on('input', function() {
		const level = parseInt($(this).val());
		updateGaugeFill(level);
		updateMarkers(level);
		updateValue(level);
		setFuelLevel(level);
	});
}

function draw_fuel_gauge(direction, value) {
	const canvas = document.getElementById(`fuel-gauge-${direction}`);
	if (!canvas) return;

	const ctx = canvas.getContext('2d');
	const centerX = canvas.width / 2;
	const centerY = canvas.height - 20;
	const radius = 80;

	// Clear canvas
	ctx.clearRect(0, 0, canvas.width, canvas.height);

	// Draw gauge background arc
	ctx.beginPath();
	ctx.arc(centerX, centerY, radius, Math.PI, 2 * Math.PI, false);
	ctx.lineWidth = 20;
	ctx.strokeStyle = '#e0e0e0';
	ctx.stroke();

	// Draw tick marks
	for (let i = 0; i <= 8; i++) {
		const angle = Math.PI + (i * Math.PI / 8);
		const tickStart = radius - 15;
		const tickEnd = i % 2 === 0 ? radius - 25 : radius - 20;

		const x1 = centerX + tickStart * Math.cos(angle);
		const y1 = centerY + tickStart * Math.sin(angle);
		const x2 = centerX + tickEnd * Math.cos(angle);
		const y2 = centerY + tickEnd * Math.sin(angle);

		ctx.beginPath();
		ctx.moveTo(x1, y1);
		ctx.lineTo(x2, y2);
		ctx.lineWidth = i % 2 === 0 ? 3 : 2;
		ctx.strokeStyle = '#666';
		ctx.stroke();
	}

	// Calculate needle angle based on value (0-100% maps to PI to 2*PI)
	const needleAngle = Math.PI + (value / 100) * Math.PI;

	// Determine color based on fuel level
	let color;
	if (value <= 25) color = '#e74c3c';      // Red - low fuel
	else if (value <= 50) color = '#f39c12'; // Orange
	else if (value <= 75) color = '#f1c40f'; // Yellow
	else color = '#27ae60';                   // Green - full

	// Draw colored arc up to current value
	ctx.beginPath();
	ctx.arc(centerX, centerY, radius, Math.PI, needleAngle, false);
	ctx.lineWidth = 20;
	ctx.strokeStyle = color;
	ctx.stroke();

	// Draw needle
	const needleLength = radius - 25;
	const needleX = centerX + needleLength * Math.cos(needleAngle);
	const needleY = centerY + needleLength * Math.sin(needleAngle);

	// Needle base circle
	ctx.beginPath();
	ctx.arc(centerX, centerY, 8, 0, 2 * Math.PI);
	ctx.fillStyle = '#333';
	ctx.fill();

	// Needle line
	ctx.beginPath();
	ctx.moveTo(centerX, centerY);
	ctx.lineTo(needleX, needleY);
	ctx.lineWidth = 4;
	ctx.strokeStyle = '#333';
	ctx.lineCap = 'round';
	ctx.stroke();

	// Draw percentage text
	ctx.fillStyle = '#333';
	ctx.font = 'bold 24px Arial';
	ctx.textAlign = 'center';
	ctx.fillText(`${value}%`, centerX, centerY + 35);

	// Draw E and F labels
	ctx.font = 'bold 14px Arial';
	ctx.fillStyle = '#666';
	ctx.fillText('E', centerX - radius - 10, centerY + 5);
	ctx.fillText('F', centerX + radius + 10, centerY + 5);

	// Draw fuel pump icon (simple representation)
	ctx.fillStyle = '#666';
	ctx.font = '16px Arial';
	ctx.fillText('⛽', centerX + radius - 15, centerY - 10);
}

function sync_fuel_display(frm, direction) {
	// Redraw the slider with new value
	render_fuel_slider(frm, direction);
}

// ===== QUICK TAGS (Phase 2) =====

function render_quick_tags(frm, direction) {
	const field_name = `${direction}_quick_tags`;
	const wrapper = frm.fields_dict[field_name].$wrapper;
	if (!wrapper) return;

	wrapper.empty();

	const tags = [
		{ label: 'Dirty', icon: 'fa-tint', color: '#795548' },
		{ label: 'Fuel Low', icon: 'fa-gas-pump', color: '#ff9800' },
		{ label: 'Late Return', icon: 'fa-clock', color: '#f44336' },
		{ label: 'Warning Light', icon: 'fa-exclamation-triangle', color: '#ff5722' },
		{ label: 'Clean', icon: 'fa-check-circle', color: '#4caf50' },
		{ label: 'Good Condition', icon: 'fa-thumbs-up', color: '#2196f3' }
	];

	const notes_field = `${direction}_notes`;
	const current_notes = frm.doc[notes_field] || '';

	const container = $(`
		<div style="margin: 10px 0;">
			<label style="font-size: 11px; color: #888; margin-bottom: 5px; display: block;">Quick Tags</label>
			<div class="quick-tags-buttons" style="display: flex; flex-wrap: wrap; gap: 8px;">
				${tags.map(tag => `
					<button type="button" class="btn btn-xs tag-btn" data-tag="${tag.label}"
						style="background: ${current_notes.includes(`[${tag.label}]`) ? tag.color : '#e0e0e0'};
						color: ${current_notes.includes(`[${tag.label}]`) ? 'white' : '#666'};
						border: none; padding: 5px 12px; border-radius: 12px; font-size: 11px; transition: all 0.2s;">
						<i class="fa ${tag.icon}"></i> ${tag.label}
					</button>
				`).join('')}
			</div>
		</div>
	`).appendTo(wrapper);

	// Handle tag clicks
	container.find('.tag-btn').on('click', function() {
		const tag = $(this).data('tag');
		const tag_text = `[${tag}]`;
		let notes = frm.doc[notes_field] || '';

		if (notes.includes(tag_text)) {
			// Remove tag
			notes = notes.replace(tag_text, '').trim();
		} else {
			// Add tag
			notes = notes ? `${notes} ${tag_text}` : tag_text;
		}

		frm.set_value(notes_field, notes);
		render_quick_tags(frm, direction);
	});
}

// ===== DISTANCE CALCULATION (Phase 3 Logic, Phase 2 Implementation) =====

function calculate_distance(frm) {
	if (frm.doc.out_mileage && frm.doc.in_mileage) {
		const distance = frm.doc.in_mileage - frm.doc.out_mileage;
		if (distance >= 0) {
			frm.set_value('distance_traveled', distance);
		}
	}
}

// ===== TIMELINE LAYOUT CSS (Phase 2) =====

function apply_timeline_layout_css() {
	// Check if CSS already injected
	if ($('#movements-timeline-css').length) return;

	const css = `
		<style id="movements-timeline-css">
			/* Timeline Layout for Movements */
			.frappe-control[data-fieldname="out_heading"],
			.frappe-control[data-fieldname="in_heading"] {
				position: relative;
				padding-left: 40px;
				margin: 20px 0 15px 0;
			}

			.frappe-control[data-fieldname="out_heading"]:before,
			.frappe-control[data-fieldname="in_heading"]:before {
				content: "";
				position: absolute;
				left: 10px;
				top: 50%;
				transform: translateY(-50%);
				width: 20px;
				height: 20px;
				border-radius: 50%;
				border: 3px solid white;
				box-shadow: 0 2px 8px rgba(0,0,0,0.2);
			}

			.frappe-control[data-fieldname="out_heading"]:before {
				background: #ff5722; /* Orange/Red for OUT */
			}

			.frappe-control[data-fieldname="in_heading"]:before {
				background: #4caf50; /* Green for IN */
			}

			.frappe-control[data-fieldname="out_heading"]:after,
			.frappe-control[data-fieldname="in_heading"]:after {
				content: "";
				position: absolute;
				left: 19px;
				top: 100%;
				width: 2px;
				height: 100px;
				background: linear-gradient(180deg, #ddd 0%, transparent 100%);
			}

			/* Hide column breaks to create vertical flow */
			.frappe-control[data-fieldname="cb_io"] {
				display: none !important;
			}

			/* Section styling */
			.frappe-control[data-fieldname="io_section"] {
				background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
				border-radius: 8px;
				padding: 20px;
				margin: 15px 0;
				box-shadow: 0 2px 4px rgba(0,0,0,0.05);
			}

			/* Vehicle Condition Section styling */
			.frappe-control[data-fieldname="vehicle_condition_section"] {
				background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
				border-left: 4px solid #4caf50;
				padding: 20px;
				margin: 20px 0;
				border-radius: 8px;
			}

			/* Damage marker styling */
			.damage-marker-container {
				animation: fadeIn 0.5s ease-in;
			}

			@keyframes fadeIn {
				from { opacity: 0; transform: translateY(10px); }
				to { opacity: 1; transform: translateY(0); }
			}

			/* Fuel slider styling enhancements */
			.fuel-slider::-webkit-slider-thumb {
				appearance: none;
				width: 20px;
				height: 20px;
				border-radius: 50%;
				background: #2196f3;
				cursor: pointer;
				box-shadow: 0 2px 4px rgba(0,0,0,0.2);
				transition: all 0.2s;
			}

			.fuel-slider::-webkit-slider-thumb:hover {
				background: #1976d2;
				transform: scale(1.2);
			}

			.fuel-slider::-moz-range-thumb {
				width: 20px;
				height: 20px;
				border-radius: 50%;
				background: #2196f3;
				cursor: pointer;
				border: none;
				box-shadow: 0 2px 4px rgba(0,0,0,0.2);
			}

			/* Quick tags hover effects */
			.tag-btn:hover {
				transform: translateY(-2px);
				box-shadow: 0 2px 8px rgba(0,0,0,0.15);
			}

			/* Responsive adjustments */
			@media (max-width: 768px) {
				.frappe-control[data-fieldname="custom_column_break_xh4dg"],
				.frappe-control[data-fieldname="custom_column_break_f87lx"],
				.frappe-control[data-fieldname="custom_column_break_1sywl"],
				.frappe-control[data-fieldname="custom_column_break_ibo93"] {
					display: none !important;
				}
			}
		</style>
	`;

	$('head').append(css);
}

// ===== STATUS BADGE (Phase 2) =====

function render_status_badge(frm) {
	// Remove existing badge
	$('.movement-status-badge').remove();

	const status = frm.doc.status || 'Draft';
	const badges = {
		'Draft': { color: '#9e9e9e', icon: 'fa-file-o' },
		'Out Only': { color: '#ff9800', icon: 'fa-arrow-circle-right' },
		'Returned': { color: '#4caf50', icon: 'fa-check-circle' },
		'Issue Flagged': { color: '#f44336', icon: 'fa-exclamation-circle' }
	};

	const badge_info = badges[status] || badges['Draft'];

	const badge = $(`
		<div class="movement-status-badge" style="
			position: fixed;
			top: 60px;
			right: 20px;
			background: ${badge_info.color};
			color: white;
			padding: 8px 16px;
			border-radius: 20px;
			font-weight: bold;
			font-size: 13px;
			box-shadow: 0 4px 12px rgba(0,0,0,0.2);
			z-index: 100;
			animation: slideIn 0.3s ease-out;
		">
			<i class="fa ${badge_info.icon}"></i> ${status}
		</div>
	`);

	$('body').append(badge);

	// Add slide-in animation
	$('head').append(`
		<style>
			@keyframes slideIn {
				from { transform: translateX(100%); opacity: 0; }
				to { transform: translateX(0); opacity: 1; }
			}
		</style>
	`);
}

// ===== DAMAGE DETECTION ALERTS (Phase 3) =====

function check_damage_alerts(frm) {
	// Check both OUT and IN damages
	const out_damages = frm.doc.out_vehicle_damage_logs || [];
	const in_damages = frm.doc.in_vehicle_damage_logs || [];
	const damages = [...out_damages, ...in_damages];

	// Check for critical damages
	const critical_damages = damages.filter(d => d.severity === 'Critical');
	if (critical_damages.length > 0) {
		frappe.msgprint({
			title: __('Critical Damage Alert'),
			message: __(
				'<strong>{0} critical damage(s) detected!</strong><br><br>Affected zones:<br>{1}',
				[critical_damages.length, critical_damages.map(d => `• ${d.zone} (${d.damage_type})`).join('<br>')]
			),
			indicator: 'red',
			primary_action: {
				label: __('Review Damages'),
				action: function() {
					frm.scroll_to_field('in_vehicle_damage_logs');
				}
			}
		});

		// Auto-flag status
		if (frm.doc.status !== 'Issue Flagged') {
			frm.set_value('status', 'Issue Flagged');
		}
	}

	// Check for severe damages
	const severe_damages = damages.filter(d => d.severity === 'Severe');
	if (severe_damages.length > 0 && critical_damages.length === 0) {
		frappe.show_alert({
			message: __('Warning: {0} severe damage(s) detected', [severe_damages.length]),
			indicator: 'orange'
		}, 7);
	}

	// Check fuel level warnings
	if (frm.doc.in_fuel_percentage !== undefined && frm.doc.in_fuel_percentage < 25) {
		frappe.show_alert({
			message: __('Low fuel level on return: {0}%', [frm.doc.in_fuel_percentage]),
			indicator: 'orange'
		}, 5);
	}

	// Check mileage anomalies
	if (frm.doc.distance_traveled && frm.doc.distance_traveled > 500) {
		frappe.msgprint({
			title: __('High Distance Alert'),
			message: __('Distance traveled ({0} km) exceeds 500 km. Please verify mileage readings.', [frm.doc.distance_traveled]),
			indicator: 'yellow'
		});
	}

	// Check for negative distance
	if (frm.doc.in_mileage && frm.doc.out_mileage && frm.doc.in_mileage < frm.doc.out_mileage) {
		frappe.msgprint({
			title: __('Mileage Error'),
			message: __('IN mileage ({0}) is less than OUT mileage ({1}). Please check odometer readings.',
				[frm.doc.in_mileage, frm.doc.out_mileage]),
			indicator: 'red'
		});
	}
}

function validate_movement_data(frm) {
	let errors = [];

	// Required field checks
	if (frm.doc.out_date_time && frm.doc.in_date_time) {
		const out_time = new Date(frm.doc.out_date_time);
		const in_time = new Date(frm.doc.in_date_time);

		if (in_time < out_time) {
			errors.push(__('IN time cannot be before OUT time'));
		}
	}

	// Fuel percentage validation
	if (frm.doc.out_fuel_percentage !== undefined && (frm.doc.out_fuel_percentage < 0 || frm.doc.out_fuel_percentage > 100)) {
		errors.push(__('OUT fuel percentage must be between 0 and 100'));
	}

	if (frm.doc.in_fuel_percentage !== undefined && (frm.doc.in_fuel_percentage < 0 || frm.doc.in_fuel_percentage > 100)) {
		errors.push(__('IN fuel percentage must be between 0 and 100'));
	}

	// Display errors
	if (errors.length > 0) {
		frappe.msgprint({
			title: __('Validation Errors'),
			message: errors.join('<br>'),
			indicator: 'red'
		});
		frappe.validated = false;
	}
}

// ===== CONDITION DELTA DISPLAY (Phase 3) =====


// ===== UI POLISH (Phase 4) =====

function auto_collapse_sections(frm) {
	// Auto-collapse sections on new documents for cleaner initial view
	if (frm.doc.__islocal) {
		setTimeout(() => {
			// Collapse workshop section by default
			frm.collapse_section('workshop_section');

			// Keep vehicle condition expanded if there are damages
			const has_out_damages = (frm.doc.out_vehicle_damage_logs || []).length > 0;
			const has_in_damages = (frm.doc.in_vehicle_damage_logs || []).length > 0;
			const has_damages = has_out_damages || has_in_damages;
			if (!has_damages) {
				frm.collapse_section('vehicle_condition_section');
			}
		}, 300);
	}

	// Add expand/collapse all button
	if (!$('.expand-collapse-all-btn').length && frm.doc.docstatus === 0) {
		// Find a reliable place to add the button
		const page_head = frm.page.page_form || $('.page-form');

		const btn = $(`
			<button class="btn btn-xs btn-default expand-collapse-all-btn" style="margin-left: 10px; margin-bottom: 10px;">
				<i class="fa fa-compress"></i> Toggle Sections
			</button>
		`);

		// Insert after the form toolbar
		if ($('.form-toolbar').length) {
			btn.insertAfter('.form-toolbar');
		} else if ($('.page-head-content').length) {
			btn.appendTo('.page-head-content');
		} else {
			btn.prependTo(page_head);
		}

		btn.on('click', function(e) {
			e.preventDefault();
			e.stopPropagation();

			const sections = ['vehicle_condition_section', 'workshop_section'];
			const icon = $(this).find('i');

			// Check first section state to determine action
			const first_section_collapsed = frm.layout.sections_dict['vehicle_condition_section'] &&
				frm.layout.sections_dict['vehicle_condition_section'].is_collapsed();

			sections.forEach(section => {
				if (frm.layout.sections_dict[section]) {
					if (first_section_collapsed) {
						frm.layout.sections_dict[section].collapse(false);
					} else {
						frm.layout.sections_dict[section].collapse(true);
					}
				}
			});

			// Update icon
			if (first_section_collapsed) {
				icon.removeClass('fa-compress').addClass('fa-expand');
			} else {
				icon.removeClass('fa-expand').addClass('fa-compress');
			}
		});
	}
}

function add_sticky_save_button(frm) {
	// Remove existing sticky button
	$('.sticky-save-btn').remove();

	if (frm.doc.docstatus !== 0) return; // Only show for draft documents

	// Create sticky save button
	const sticky_btn = $(`
		<div class="sticky-save-btn" style="
			position: fixed;
			bottom: 30px;
			right: 30px;
			z-index: 1000;
			box-shadow: 0 4px 16px rgba(0,0,0,0.3);
			border-radius: 50px;
			overflow: hidden;
			transition: all 0.3s ease;
		">
			<button class="btn btn-primary btn-lg" style="
				padding: 12px 30px;
				font-size: 16px;
				font-weight: bold;
				border-radius: 50px;
				border: none;
				display: flex;
				align-items: center;
				gap: 10px;
			">
				<i class="fa fa-save"></i>
				<span>Save Movement</span>
			</button>
		</div>
	`);

	$('body').append(sticky_btn);

	// Handle click
	sticky_btn.find('button').on('click', function() {
		frm.save();

		// Visual feedback
		$(this).html('<i class="fa fa-check"></i> <span>Saving...</span>');

		setTimeout(() => {
			sticky_btn.find('button').html('<i class="fa fa-save"></i> <span>Save Movement</span>');
		}, 1500);
	});

	// Show/hide on scroll
	let lastScroll = 0;
	$(window).on('scroll', function() {
		const currentScroll = $(this).scrollTop();

		if (currentScroll > 200) {
			sticky_btn.css('opacity', '1');
		} else {
			sticky_btn.css('opacity', '0.7');
		}

		lastScroll = currentScroll;
	});

	// Hover effect
	sticky_btn.hover(
		function() {
			$(this).css('transform', 'scale(1.05)');
		},
		function() {
			$(this).css('transform', 'scale(1)');
		}
	);

	// Add CSS for animations
	$('head').append(`
		<style>
			.sticky-save-btn {
				animation: slideUp 0.5s ease-out;
			}

			@keyframes slideUp {
				from {
					transform: translateY(100px);
					opacity: 0;
				}
				to {
					transform: translateY(0);
					opacity: 1;
				}
			}

			@media (max-width: 768px) {
				.sticky-save-btn {
					bottom: 15px;
					right: 15px;
				}

				.sticky-save-btn button {
					padding: 10px 20px !important;
					font-size: 14px !important;
				}
			}
		</style>
	`);
}

// ===== REPLACEMENT WORKFLOW FUNCTIONS =====

function setup_replacement_workflow_buttons(frm) {
	// Only show buttons for saved documents in draft state
	if (frm.doc.__islocal || frm.doc.docstatus !== 0) return;

	const movement_type = frm.doc.movement_type;

	// Clear existing replacement workflow buttons
	frm.remove_custom_button(__('Create Replacement Movement'), __('Replacement Workflow'));
	frm.remove_custom_button(__('Create Workshop Movement'), __('Replacement Workflow'));
	frm.remove_custom_button(__('Start Replacement Workflow'), __('Replacement Workflow'));

	// Show buttons based on movement type and state
	if (movement_type === 'Replacement - Customer Return') {
		// Customer's vehicle is IN - offer to create replacement vehicle OUT
		if (frm.doc.in_date_time && !frm.doc.replacement_vehicle) {
			frm.add_custom_button(__('Give Replacement Vehicle'), function() {
				create_replacement_vehicle_out_movement(frm);
			}, __('Replacement Workflow'));
		}

		// After replacement vehicle is given, offer to send original to workshop
		if (frm.doc.in_date_time) {
			frm.add_custom_button(__('Send to Workshop'), function() {
				create_workshop_movement(frm);
			}, __('Replacement Workflow'));
		}
	}

	// For any movement type, allow starting a replacement workflow
	if (!movement_type || !movement_type.includes('Replacement')) {
		if (frm.doc.vehicle && frm.doc.agreement_type && frm.doc.agreement_no) {
			frm.add_custom_button(__('Start Replacement Workflow'), function() {
				start_replacement_workflow(frm);
			}, __('Replacement Workflow'));
		}
	}

	// For Workshop movements linked to a replacement flow
	if (movement_type === 'Workshop' && frm.doc.parent_movement) {
		frm.add_custom_button(__('View Parent Movement'), function() {
			frappe.set_route('Form', 'Movements', frm.doc.parent_movement);
		}, __('Replacement Workflow'));
	}

	// For Replacement - Vehicle Out, show link to parent
	if (movement_type === 'Replacement - Vehicle Out' && frm.doc.parent_movement) {
		frm.add_custom_button(__('View Customer Return'), function() {
			frappe.set_route('Form', 'Movements', frm.doc.parent_movement);
		}, __('Replacement Workflow'));
	}
}

function show_linked_movements(frm) {
	// Only show for saved documents
	if (frm.doc.__islocal) return;

	// Check if this movement has linked movements
	if (frm.doc.is_replacement || frm.doc.parent_movement) {
		// Fetch linked movements
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Movements',
				filters: [
					['name', '!=', frm.doc.name],
					['|', ['parent_movement', '=', frm.doc.name], ['name', '=', frm.doc.parent_movement || '']]
				],
				fields: ['name', 'movement_type', 'vehicle', 'status', 'out_date_time', 'in_date_time'],
				limit_page_length: 10
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					render_linked_movements_section(frm, r.message);
				}
			}
		});
	}
}

function render_linked_movements_section(frm, linked_movements) {
	// Find or create linked movements display area
	let linked_html = frm.fields_dict.replacement_section;
	if (!linked_html || !linked_html.$wrapper) return;

	// Remove existing linked movements display
	linked_html.$wrapper.find('.linked-movements-display').remove();

	let html = `
		<div class="linked-movements-display" style="background: #e3f2fd; border-radius: 8px; padding: 15px; margin: 15px 0;">
			<h6 style="margin-bottom: 10px; color: #1976d2;">
				<i class="fa fa-link"></i> Linked Movements
			</h6>
			<div class="linked-movements-list">
	`;

	linked_movements.forEach(mov => {
		const status_color = {
			'Draft': '#9e9e9e',
			'Out Only': '#ff9800',
			'Returned': '#4caf50',
			'Issue Flagged': '#f44336'
		}[mov.status] || '#9e9e9e';

		html += `
			<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; background: white; border-radius: 4px; margin-bottom: 8px;">
				<div>
					<a href="/app/movements/${mov.name}" style="font-weight: bold;">${mov.name}</a>
					<span style="color: #666; margin-left: 10px;">${mov.movement_type}</span>
				</div>
				<div style="display: flex; align-items: center; gap: 10px;">
					<span style="color: #666; font-size: 12px;">${mov.vehicle}</span>
					<span style="background: ${status_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">${mov.status}</span>
				</div>
			</div>
		`;
	});

	html += `
			</div>
		</div>
	`;

	linked_html.$wrapper.append(html);
}

function create_replacement_vehicle_out_movement(frm) {
	// Dialog to select replacement vehicle
	let d = new frappe.ui.Dialog({
		title: __('Give Replacement Vehicle to Customer'),
		fields: [
			{
				fieldname: 'info_html',
				fieldtype: 'HTML',
				options: `
					<div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
						<p style="margin: 0;"><strong>Customer's vehicle:</strong> ${frm.doc.vehicle}</p>
						<p style="margin: 5px 0 0;"><strong>Agreement:</strong> ${frm.doc.agreement_no || 'Not linked'}</p>
					</div>
				`
			},
			{
				fieldname: 'replacement_vehicle',
				fieldtype: 'Link',
				label: __('Select Replacement Vehicle'),
				options: 'Vehicle',
				reqd: 1,
				get_query: function() {
					return {
						filters: {
							status: ['in', ['Available', 'Ready']],
							name: ['!=', frm.doc.vehicle]
						}
					};
				}
			},
			{
				fieldname: 'out_date_time',
				fieldtype: 'Datetime',
				label: __('OUT Date/Time'),
				default: frappe.datetime.now_datetime(),
				reqd: 1
			},
			{
				fieldname: 'out_fuel_percentage',
				fieldtype: 'Int',
				label: __('Fuel Level (%)'),
				default: 100
			},
			{
				fieldname: 'out_mileage',
				fieldtype: 'Float',
				label: __('OUT Mileage')
			}
		],
		primary_action_label: __('Create Replacement Movement'),
		primary_action: function(values) {
			frappe.call({
				method: 'frappe.client.insert',
				args: {
					doc: {
						doctype: 'Movements',
						movement_type: 'Replacement - Vehicle Out',
						vehicle: frm.doc.vehicle,
						replacement_vehicle: values.replacement_vehicle,
						parent_movement: frm.doc.name,
						is_replacement: 1,
						agreement_type: frm.doc.agreement_type,
						agreement_no: frm.doc.agreement_no,
						date: frappe.datetime.get_today(),
						out_date_time: values.out_date_time,
						out_fuel_percentage: values.out_fuel_percentage,
						out_mileage: values.out_mileage,
						out_customer: frm.doc.in_customer,
						out_driver: frm.doc.in_driver,
						status: 'Out Only'
					}
				},
				callback: function(r) {
					if (r.message) {
						// Update current movement with replacement vehicle reference
						frm.set_value('replacement_vehicle', values.replacement_vehicle);
						frm.save();

						frappe.show_alert({
							message: __('Replacement movement {0} created', [r.message.name]),
							indicator: 'green'
						});

						d.hide();

						// Ask if user wants to open the new movement
						frappe.confirm(
							__('Replacement movement created. Do you want to open it?'),
							function() {
								frappe.set_route('Form', 'Movements', r.message.name);
							}
						);
					}
				}
			});
		}
	});

	d.show();
}

function create_workshop_movement(frm) {
	// Dialog to create workshop movement for the original vehicle
	let d = new frappe.ui.Dialog({
		title: __('Send Vehicle to Workshop'),
		fields: [
			{
				fieldname: 'info_html',
				fieldtype: 'HTML',
				options: `
					<div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
						<p style="margin: 0;"><strong>Vehicle to send:</strong> ${frm.doc.vehicle}</p>
						<p style="margin: 5px 0 0;">This vehicle will be sent to the workshop for repair/service.</p>
					</div>
				`
			},
			{
				fieldname: 'workshop',
				fieldtype: 'Link',
				label: __('Workshop'),
				options: 'Workshop'
			},
			{
				fieldname: 'out_date_time',
				fieldtype: 'Datetime',
				label: __('OUT Date/Time (to workshop)'),
				default: frappe.datetime.now_datetime(),
				reqd: 1
			},
			{
				fieldname: 'out_mileage',
				fieldtype: 'Float',
				label: __('OUT Mileage'),
				default: frm.doc.in_mileage
			},
			{
				fieldname: 'out_notes',
				fieldtype: 'Small Text',
				label: __('Notes'),
				description: __('Describe the reason for workshop visit')
			}
		],
		primary_action_label: __('Create Workshop Movement'),
		primary_action: function(values) {
			frappe.call({
				method: 'frappe.client.insert',
				args: {
					doc: {
						doctype: 'Movements',
						movement_type: 'Workshop',
						vehicle: frm.doc.vehicle,
						parent_movement: frm.doc.name,
						workshop: values.workshop,
						agreement_type: frm.doc.agreement_type,
						agreement_no: frm.doc.agreement_no,
						date: frappe.datetime.get_today(),
						out_date_time: values.out_date_time,
						out_mileage: values.out_mileage,
						out_notes: values.out_notes,
						status: 'Out Only'
					}
				},
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: __('Workshop movement {0} created', [r.message.name]),
							indicator: 'green'
						});

						d.hide();

						// Ask if user wants to open the new movement
						frappe.confirm(
							__('Workshop movement created. Do you want to open it?'),
							function() {
								frappe.set_route('Form', 'Movements', r.message.name);
							}
						);
					}
				}
			});
		}
	});

	d.show();
}

function start_replacement_workflow(frm) {
	// Full guided replacement workflow
	frappe.confirm(
		__('This will start a replacement workflow where:<br><br>' +
		   '1. Customer\'s vehicle ({0}) comes IN for repair<br>' +
		   '2. A replacement vehicle goes OUT to customer<br>' +
		   '3. Original vehicle goes to workshop<br><br>' +
		   'Continue?', [frm.doc.vehicle]),
		function() {
			// Create the Customer Return movement
			let d = new frappe.ui.Dialog({
				title: __('Step 1: Record Customer Vehicle Return'),
				fields: [
					{
						fieldname: 'info_html',
						fieldtype: 'HTML',
						options: `
							<div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
								<h6 style="margin: 0 0 10px;"><i class="fa fa-car"></i> Vehicle Coming IN</h6>
								<p style="margin: 0;"><strong>Vehicle:</strong> ${frm.doc.vehicle}</p>
								<p style="margin: 5px 0 0;"><strong>Agreement:</strong> ${frm.doc.agreement_no || 'Not linked'}</p>
							</div>
						`
					},
					{
						fieldname: 'in_date_time',
						fieldtype: 'Datetime',
						label: __('IN Date/Time'),
						default: frappe.datetime.now_datetime(),
						reqd: 1
					},
					{
						fieldname: 'in_mileage',
						fieldtype: 'Float',
						label: __('IN Mileage')
					},
					{
						fieldname: 'in_fuel_percentage',
						fieldtype: 'Int',
						label: __('Fuel Level (%)'),
						default: 50
					},
					{
						fieldname: 'in_customer',
						fieldtype: 'Link',
						label: __('Customer'),
						options: 'Customer'
					},
					{
						fieldname: 'in_driver',
						fieldtype: 'Data',
						label: __('Driver Name')
					},
					{
						fieldname: 'in_notes',
						fieldtype: 'Small Text',
						label: __('Reason for Return'),
						description: __('e.g., Vehicle needs repair, scheduled maintenance')
					}
				],
				primary_action_label: __('Record Return & Continue'),
				primary_action: function(values) {
					frappe.call({
						method: 'frappe.client.insert',
						args: {
							doc: {
								doctype: 'Movements',
								movement_type: 'Replacement - Customer Return',
								vehicle: frm.doc.vehicle,
								is_replacement: 1,
								agreement_type: frm.doc.agreement_type,
								agreement_no: frm.doc.agreement_no,
								date: frappe.datetime.get_today(),
								in_date_time: values.in_date_time,
								in_mileage: values.in_mileage,
								in_fuel_percentage: values.in_fuel_percentage,
								in_customer: values.in_customer,
								in_driver: values.in_driver,
								in_notes: values.in_notes,
								status: 'Returned'
							}
						},
						callback: function(r) {
							if (r.message) {
								d.hide();
								frappe.show_alert({
									message: __('Customer return recorded'),
									indicator: 'green'
								});

								// Open the new movement to continue workflow
								frappe.set_route('Form', 'Movements', r.message.name);
							}
						}
					});
				}
			});

			d.show();
		}
	);
}

