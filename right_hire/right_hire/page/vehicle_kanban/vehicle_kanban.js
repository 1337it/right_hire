frappe.pages['vehicle-kanban'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Vehicle Fleet Board',
		single_column: true
	});

	// Add filters
	page.add_field({
		fieldname: 'branch',
		label: __('Branch'),
		fieldtype: 'Link',
		options: 'Branch',
		change: function() {
			page.vehicle_kanban.refresh();
		}
	});

	page.add_field({
		fieldname: 'body_type',
		label: __('Vehicle Type'),
		fieldtype: 'Select',
		options: '\nSedan\nSUV\nHatchback\nVan\nTruck\nLuxury',
		change: function() {
			page.vehicle_kanban.refresh();
		}
	});

	// Add refresh button
	page.set_primary_action(__('Refresh'), function() {
		page.vehicle_kanban.refresh();
	}, 'refresh');

	// Initialize Kanban
	page.vehicle_kanban = new VehicleKanban(page);
};

frappe.pages['vehicle-kanban'].on_page_show = function(wrapper) {
	wrapper.page.vehicle_kanban.refresh();
};

class VehicleKanban {
	constructor(page) {
		this.page = page;
		this.wrapper = $('<div class="vehicle-kanban-wrapper"></div>').appendTo(page.body);
		this.statuses = [];
		this.vehicles = [];
		this.setup();
	}

	setup() {
		this.add_styles();
		this.load_statuses();
	}

	add_styles() {
		if (!document.getElementById('vehicle-kanban-styles')) {
			const styles = `
				<style id="vehicle-kanban-styles">
					.vehicle-kanban-wrapper {
						padding: 10px;
						overflow-x: auto;
						height: calc(100vh - 60px);
					}
					#page-vehicle-kanban .page-form.row {
						display: none !important;
					}
					.kanban-board {
						display: flex;
						gap: 8px;
						height: 100%;
					}
					.kanban-column {
						min-width: 180px;
						width: 180px;
						flex-shrink: 0;
						background: var(--fg-color);
						border-radius: 6px;
						border: 1px solid var(--border-color);
						display: flex;
						flex-direction: column;
						height: 100%;
						transition: min-width 0.3s ease, width 0.3s ease;
					}
					.kanban-board.dragging-active {
						flex-wrap: nowrap;
						overflow-x: hidden;
					}
					.kanban-board.dragging-active .kanban-column {
						min-width: 70px !important;
						width: calc((100vw - 60px) / var(--column-count, 11)) !important;
						flex-shrink: 1 !important;
					}
					.kanban-board.dragging-active .kanban-column-header {
						font-size: 8px;
						padding: 4px 6px;
						white-space: nowrap;
						overflow: hidden;
						text-overflow: ellipsis;
					}
					.kanban-board.dragging-active .kanban-column-header .count {
						font-size: 8px;
						padding: 0 4px;
					}
					.kanban-board.dragging-active .kanban-column-body {
						padding: 4px;
					}
					.kanban-board.dragging-active .vehicle-card {
						padding: 3px;
						margin-bottom: 3px;
					}
					.kanban-board.dragging-active .kanban-plate {
						margin-bottom: 2px;
					}
					.kanban-board.dragging-active .kanban-plate-inner {
						aspect-ratio: 4/1;
					}
					.kanban-board.dragging-active .kanban-plate-left {
						display: none;
					}
					.kanban-board.dragging-active .kanban-plate-number {
						font-size: 10px;
						padding-right: 4px;
					}
					.kanban-board.dragging-active .vehicle-meta,
					.kanban-board.dragging-active .vehicle-links,
					.kanban-board.dragging-active .alert-badge {
						display: none;
					}
					.kanban-column-header {
						padding: 8px 10px;
						border-radius: 6px 6px 0 0;
						font-weight: 600;
						font-size: 11px;
						display: flex;
						justify-content: space-between;
						align-items: center;
					}
					.kanban-column-header .count {
						background: rgba(255,255,255,0.3);
						padding: 1px 6px;
						border-radius: 8px;
						font-size: 10px;
					}
					.kanban-column-body {
						flex: 1;
						padding: 6px;
						overflow-y: auto;
						overflow-x: hidden;
					}
					.vehicle-card {
						background: var(--card-bg);
						border: 1px solid var(--border-color);
						border-radius: 4px;
						padding: 6px;
						margin-bottom: 6px;
						cursor: grab;
						transition: all 0.3s ease;
						overflow: hidden;
					}
					.vehicle-card .vehicle-meta {
						max-height: 0;
						opacity: 0;
						overflow: hidden;
						transition: max-height 0.3s ease, opacity 0.3s ease, margin 0.3s ease;
						margin-top: 0;
					}
					.vehicle-card:hover .vehicle-meta {
						max-height: 150px;
						opacity: 1;
						margin-top: 4px;
					}
					.vehicle-card:hover {
						box-shadow: 0 4px 12px rgba(0,0,0,0.15);
						z-index: 10;
					}
					.vehicle-card.dragging {
						opacity: 0.5;
						cursor: grabbing;
					}
					/* Dubai Plate Styling for Kanban Cards */
					.kanban-plate {
						width: 100%;
						margin-bottom: 4px;
					}
					.kanban-plate-inner {
						height: auto;
						aspect-ratio: 5/1;
						width: 100%;
						background: #ffffff;
						border-radius: 4px;
						box-shadow: 0 0 0 1px #555, 0 0 0 3px #222;
						display: flex;
						overflow: hidden;
						position: relative;
					}
					.kanban-plate-inner::after {
						content: "";
						position: absolute;
						inset: 2px;
						border-radius: 2px;
						border: 1px solid rgba(255,255,255,0.7);
						pointer-events: none;
					}
					.kanban-plate-left {
						position: relative;
						z-index: 1;
						width: 40%;
						display: flex;
						flex-direction: column;
						align-items: center;
						justify-content: center;
						padding-left: 25px;
					}
					.kanban-plate-logo {
						width: 90%;
						height: auto;
						display: block;
					}
					.kanban-plate-code {
						font-family: "Arial Black", sans-serif;
						font-size: 9px;
						line-height: 1;
						color: #464646;
						margin-top: 1px;
					}
					.kanban-plate-right {
						flex: 1;
						display: flex;
						justify-content: flex-end;
						align-items: center;
						padding-right: 20px;
						z-index: 1;
					}
					.kanban-plate-number {
						font-family: "Arial Narrow", sans-serif;
						font-weight: 700;
						font-size: 18px;
						line-height: 1;
						color: #464646;
						letter-spacing: 0.1em;
						text-align: right;
					}
					[data-theme="dark"] .kanban-plate-inner {
						filter: invert(1);
					}
					.vehicle-card .vehicle-meta {
						font-size: 11px;
						color: var(--text-color);
						margin-top: 4px;
					}
					.vehicle-card .vehicle-meta .model {
						white-space: nowrap;
						overflow: hidden;
						text-overflow: ellipsis;
						margin-bottom: 4px;
						font-weight: 600;
						font-size: 12px;
					}
					.vehicle-card .vehicle-meta .detail-row {
						display: flex;
						justify-content: space-between;
						margin-bottom: 3px;
						font-size: 10px;
					}
					.vehicle-card .vehicle-meta .detail-label {
						color: var(--text-muted);
					}
					.vehicle-card .vehicle-meta .detail-value {
						font-weight: 500;
					}
					.vehicle-card .vehicle-meta .period {
						font-size: 10px;
						color: var(--text-muted);
						margin-top: 4px;
						padding-top: 4px;
						border-top: 1px solid var(--border-color);
					}
					.vehicle-card .vehicle-links {
						display: flex;
						flex-direction: column;
						gap: 2px;
						margin-top: 3px;
					}
					.vehicle-card .vehicle-links a {
						font-size: 8px;
						color: var(--primary-color);
						text-decoration: none;
						white-space: nowrap;
						overflow: hidden;
						text-overflow: ellipsis;
						display: block;
					}
					.vehicle-card .vehicle-links a:hover {
						text-decoration: underline;
					}
					.vehicle-card .agreement-link,
					.vehicle-card .model,
					.vehicle-card .customer-link {
						display: flex;
						flex-direction: column;
						gap: 2px;
						margin-top: 3px;
						color: black !important;
					}
					.vehicle-card .vehicle-links .link-label {
						color: var(--text-muted);
						font-weight: 500;
					}
					.vehicle-card .alert-badge {
						font-size: 8px;
						padding: 1px 4px;
						border-radius: 2px;
						margin-top: 3px;
						display: inline-block;
					}
					.vehicle-card .alert-badge.low-fuel {
						background: #fef3c7;
						color: #d97706;
					}
					.kanban-column.drag-over {
						background: var(--bg-light-gray);
					}
					.color-gray { background: linear-gradient(135deg, #8e9aaf 0%, #a8b2c1 100%); color: white; }
					.color-green { background: linear-gradient(135deg, #52b788 0%, #74c69d 100%); color: white; }
					.color-blue { background: linear-gradient(135deg, #5390d9 0%, #7eb8da 100%); color: white; }
					.color-orange { background: linear-gradient(135deg, #e9a84a 0%, #f4c479 100%); color: white; }
					.color-red { background: linear-gradient(135deg, #e07a7a 0%, #ef9a9a 100%); color: white; }
					.color-purple { background: linear-gradient(135deg, #9575cd 0%, #b39ddb 100%); color: white; }
					.color-yellow { background: linear-gradient(135deg, #d4a84b 0%, #e8c87a 100%); color: #333; }
					.color-pink { background: linear-gradient(135deg, #d48cb3 0%, #e8b4cf 100%); color: white; }
				</style>
			`;
			$(styles).appendTo('head');
		}
	}

	load_statuses() {
		frappe.call({
			method: 'right_hire.right_hire.doctype.vehicle_status.vehicle_status.get_kanban_settings',
			callback: (r) => {
				if (r.message) {
					this.statuses = r.message;
				} else {
					this.statuses = this.get_default_statuses();
				}
				this.refresh();
			},
			error: () => {
				this.statuses = this.get_default_statuses();
				this.refresh();
			}
		});
	}

	get_default_statuses() {
		return [
			{ status_name: 'Available', display_order: 1, color: 'green' },
			{ status_name: 'Reserved', display_order: 2, color: 'blue' },
			{ status_name: 'Out for Delivery', display_order: 3, color: 'purple' },
			{ status_name: 'Rented Out', display_order: 4, color: 'orange' },
			{ status_name: 'Leased', display_order: 5, color: 'orange' },
			{ status_name: 'Due for Return', display_order: 6, color: 'yellow' },
			{ status_name: 'Custody', display_order: 7, color: 'gray' },
			{ status_name: 'At Garage', display_order: 8, color: 'red' },
			{ status_name: 'Under Maintenance', display_order: 9, color: 'red' },
			{ status_name: 'Accident/Repair', display_order: 10, color: 'red' },
			{ status_name: 'Deactivated', display_order: 11, color: 'gray' }
		];
	}

	refresh() {
		this.load_vehicles();
	}

	load_vehicles() {
		const filters = {};

		const branch = this.page.fields_dict.branch.get_value();
		const body_type = this.page.fields_dict.body_type.get_value();

		if (branch) filters.branch = branch;
		if (body_type) filters.body_type = body_type;

		frappe.call({
			method: 'right_hire.right_hire.doctype.vehicle_status.vehicle_status.get_kanban_vehicles',
			args: {
				filters: JSON.stringify(filters)
			},
			callback: (r) => {
				this.vehicles = r.message || [];
				this.render();
			}
		});
	}

	render() {
		this.wrapper.empty();

		const board = $('<div class="kanban-board"></div>').appendTo(this.wrapper);

		this.statuses.forEach(status => {
			const vehicles_in_status = this.vehicles.filter(v => v.status === status.status_name);
			const column = this.create_column(status, vehicles_in_status);
			board.append(column);
		});

		this.setup_drag_drop();
	}

	create_column(status, vehicles) {
		const column = $(`
			<div class="kanban-column" data-status="${status.status_name}">
				<div class="kanban-column-header color-${status.color}">
					<span>${status.status_name}</span>
					<span class="count">${vehicles.length}</span>
				</div>
				<div class="kanban-column-body">
				</div>
			</div>
		`);

		const body = column.find('.kanban-column-body');

		vehicles.forEach(vehicle => {
			const card = this.create_card(vehicle, status.color);
			body.append(card);
		});

		return column;
	}

	create_card(vehicle, color) {
		const alerts = this.get_alerts(vehicle);
		const alerts_html = alerts.map(a => `<span class="alert-badge ${a.class}">${a.label}</span>`).join('');

		const plate_code = vehicle.plate_code || vehicle.custom_plate_code || '';
		const plate_no = vehicle.plate_no || vehicle.name;
		const model_text = [vehicle.make, vehicle.model, vehicle.year].filter(Boolean).join(' ');

		// Format mileage
		const mileage = vehicle.odometer ? this.format_number(vehicle.odometer) + ' km' : '-';

		// Build links HTML for agreement/customer/workshop
		let links_html = '';
		let period_html = '';
		if (vehicle.agreement_info) {
			const agr = vehicle.agreement_info;
			links_html += `<a href="/app/${frappe.router.slug(agr.agreement_type)}/${agr.agreement_no}" class="agreement-link" data-doctype="${agr.agreement_type}" data-name="${agr.agreement_no}"><span class="link-label">Agr:</span> ${agr.agreement_no}</a>`;
			if (agr.customer_name) {
				links_html += `<a href="/app/customer/${agr.customer}" class="customer-link" data-doctype="Customer" data-name="${agr.customer}"><span class="link-label">Cust:</span> ${agr.customer_name}</a>`;
			}
			// Build period info
			if (agr.start_date || agr.end_date) {
				const start = agr.start_date ? frappe.datetime.str_to_user(agr.start_date) : '?';
				const end = agr.end_date ? frappe.datetime.str_to_user(agr.end_date) : '?';
				period_html = `<div class="period">📅 ${start} → ${end}</div>`;
			}
		}
		if (vehicle.workshop_info) {
			const ws = vehicle.workshop_info;
			links_html += `<a href="/app/workshop/${ws.workshop}" class="workshop-link" data-doctype="Workshop" data-name="${ws.workshop}"><span class="link-label">WS:</span> ${ws.workshop_name}</a>`;
		}

		// Dubai plate SVG logo (simplified for kanban)
		const dubai_logo = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 322 124" class="kanban-plate-logo"><path d="M0 0 C47.9483871 0 47.9483871 0 53.83984375 5.81640625 C54.38318359 6.68072266 54.38318359 6.68072266 54.9375 7.5625 C55.31777344 8.14128906 55.69804688 8.72007813 56.08984375 9.31640625 C58.13977045 13.10833074 58.13707201 16.34714615 58.16113281 20.5793457 C58.16858017 21.57504074 58.16858017 21.57504074 58.17617798 22.59085083 C58.19077671 24.78583821 58.19759816 26.9807533 58.203125 29.17578125 C58.20887885 30.70411684 58.21463656 32.23245241 58.22039795 33.76078796 C58.23090178 36.96609839 58.23674831 40.17138378 58.24023438 43.37670898 C58.24571429 47.47568497 58.2697339 51.57432797 58.29820633 55.67319965 C58.31686945 58.83114068 58.32204028 61.98900213 58.32357025 65.14699364 C58.32658962 66.65761317 58.33459394 68.16823155 58.34775543 69.67879677 C58.36489163 71.79694246 58.36291769 73.91428301 58.35644531 76.0324707 C58.36191376 77.83757866 58.36191376 77.83757866 58.36749268 79.67915344 C57.6780634 85.90917923 54.72286088 90.02850335 50 94 C34.65336659 100.57712861 16.69663972 97 0 97 C0 64.99 0 32.98 0 0 Z M21 22 C21 40.15 21 58.3 21 77 C27.93872873 77 28.99559177 76.98077928 34 73 C34.54495117 72.60683594 35.08990234 72.21367188 35.65136719 71.80859375 C37.77649324 68.95867815 37.35336393 66.37711964 37.328125 62.875 C37.32625183 62.17286377 37.32437866 61.47072754 37.32244873 60.74731445 C37.31572604 59.25776436 37.30180706 57.768232 37.28125 56.27880859 C37.25049312 54.0359594 37.24031289 51.79381917 37.234375 49.55078125 C38.10374578 36.35032611 38.10374578 36.35032611 34.85791016 24.22973633 C32.11667406 21.60990169 29.98137722 20.99813772 26.25 20.625 C23.11747418 20.79886997 23.11747418 20.79886997 21 22 Z" fill="#4B9ACD" transform="translate(12,11)"/><path d="M0 0 C8.34788609 -0.33884408 14.32020727 0.96154931 20.82421875 6.57421875 C27.8885633 14.2079815 29.76689551 22.05014041 29.4375 32.34375 C28.37097268 41.25687119 24.04852522 46.59348197 17.37890625 52.30859375 C10.86169937 56.94233854 5.92275595 57.41393794 -1.8671875 57.29296875 C-2.90191193 57.28872391 -3.93663635 57.28447906 -5.00271606 57.28010559 C-8.29374681 57.26336996 -11.58415566 57.22572649 -14.875 57.1875 C-17.1119703 57.17244658 -19.34895023 57.15875933 -21.5859375 57.14648438 C-27.05750233 57.11348322 -32.52870672 57.06333468 -38 57 C-37.98768845 57.75510864 -37.97537689 58.51021729 -37.96269226 59.28820801 C-37.92875088 61.36994618 -37.89533968 63.45169306 -37.86239624 65.53344727 C-37.82571188 67.71449524 -37.78020615 69.89539935 -37.72973633 72.07617188 C-37.67213018 79.41507102 -37.93297856 85.85008609 -43.3125 91.375 C-50.67671648 95.82778206 -58.0932757 95.33316425 -66.4375 95.3125 C-67.73494141 95.32861328 -69.03238281 95.34472656 -70.36914062 95.36132812 C-78.64118902 95.36556368 -84.15066795 95.06196868 -90.75 89.8125 C-95.66450406 83.66936992 -96.46137087 77.38507946 -96.43359375 69.79296875 C-96.4388356 68.9457576 -96.44407745 68.09854645 -96.44947815 67.22566223 C-96.45585849 65.45001313 -96.45461352 63.67432153 -96.44604492 61.89868164 C-96.43746736 59.17714428 -96.46645756 56.45766228 -96.49804688 53.73632812 C-96.49965744 52.00520896 -96.49908413 50.27408608 -96.49609375 48.54296875 C-96.50732773 47.73047165 -96.51856171 46.91797455 -96.53013611 46.08085632 C-96.46099675 40.51812587 -96.46099675 40.51812587 -94.21118164 37.98950195 C-89.5404062 35.89933381 -85.32321336 36.52564049 -80.6875 38.1875 C-77.63778387 40.2442853 -76.62768512 41.7298247 -75 45 C-74.53930664 47.79907227 -74.53930664 47.79907227 -74.41015625 50.81640625 C-74.34763672 51.91017578 -74.28511719 53.00394531 -74.22070312 54.13085938 C-74.11506279 56.42234168 -74.01351321 58.71401617 -73.91601562 61.00585938 C-73.85220703 62.09833984 -73.78839844 63.19082031 -73.72265625 64.31640625 C-73.67890869 65.31099854 -73.63516113 66.30559082 -73.59008789 67.33032227 C-72.83823681 70.73184959 -71.76421263 71.91390776 -69 74 C-66.43843328 74.89561116 -66.43843328 74.89561116 -63.75 75.25 C-62.85796875 75.39953125 -61.9659375 75.5490625 -61.046875 75.703125 C-60.37140625 75.80109375 -59.6959375 75.8990625 -59 76 C-58.98018066 75.22398438 -58.96036133 74.44796875 -58.93994141 73.6484375 C-58.84410122 70.09864413 -58.73466196 66.54939219 -58.625 63 C-58.57859375 61.16888672 -58.57859375 61.16888672 -58.53125 59.30078125 C-58.32464811 52.93055642 -58.04991057 47.06219104 -56 41 C-50.15716423 35.82491689 -40.53097812 36.76664114 -33.140625 36.5 C-31.03515538 36.41668871 -28.92968665 36.33335471 -26.82421875 36.25 C-23.52364592 36.12375666 -20.22302163 35.99898658 -16.92236328 35.875 C-13.72413174 35.75361419 -10.52613712 35.62701575 -7.328125 35.5 C-6.33750061 35.46455078 -5.34687622 35.42910156 -4.32623291 35.39257812 C-3.408078 35.35583984 -2.4899231 35.31910156 -1.54394531 35.28125 C-0.73677063 35.25095703 0.07040405 35.22066406 0.90203857 35.18945312 C3.19184377 35.06362099 3.19184377 35.06362099 6 34 C7.62599875 30.7480025 7.85522404 27.48771053 7 24 C5.42702591 22.71046063 5.42702591 22.71046063 3.5 21.625 C1.55859375 20.25 1.55859375 20.25 0 18 C-0.97276494 12.08604762 -0.39283855 5.94869811 0 0 Z" fill="#C7699A" transform="translate(174,12)"/><path d="M0 0 C4.63309418 1.91182588 7.63388902 3.93922243 10.34765625 8.28125 C10.70150391 8.8371582 11.05535156 9.39306641 11.41992188 9.96582031 C12.72157324 13.21446808 12.71188093 16.37716889 12.75390625 19.828125 C12.7653064 20.55815735 12.77670654 21.2881897 12.78845215 22.04034424 C12.80730751 23.58347825 12.82040242 25.12669199 12.828125 26.66992188 C12.84748525 29.01057657 12.90952433 31.34767337 12.97265625 33.6875 C13.15790037 46.22168084 13.15790037 46.22168084 9.87890625 51.171875 C3.79423625 57.20621188 -4.32770164 57.73156001 -12.5 57.79296875 C-13.39730331 57.81091995 -14.29460663 57.82887115 -15.21910095 57.84736633 C-18.05096912 57.9010233 -20.88267317 57.93522034 -23.71484375 57.96875 C-25.64911117 58.00196257 -27.58335705 58.0364558 -29.51757812 58.07226562 C-34.22904732 58.15672347 -38.94047164 58.22374553 -43.65234375 58.28125 C-45.06257348 52.8883224 -45.63023766 47.64878262 -43.46484375 42.40625 C-40.93186812 39.43655443 -38.56029705 37.56012038 -34.59448242 36.98046875 C-32.17427126 36.83284176 -29.76421217 36.75837003 -27.33984375 36.71875 C-21.14480821 36.58673267 -15.58923469 36.16629673 -9.65234375 34.28125 C-8.08804127 31.15264505 -8.29607091 28.72522075 -8.65234375 25.28125 C-12.15404447 21.45126483 -16.99938954 19.45185891 -21.65234375 17.28125 C-22.51336234 6.52808455 -22.51336234 6.52808455 -19.27734375 2.65625 C-13.93139716 -2.18055882 -6.79019231 -1.84005211 0 0 Z" fill="#C7689A" transform="translate(256.65234375,11.71875)"/><path d="M0 0 C1.86398437 0.03673828 1.86398437 0.03673828 3.765625 0.07421875 C6.75 0.3125 6.75 0.3125 7.75 1.3125 C7.8718349 4.12131015 7.92863758 6.90595532 7.94287109 9.71606445 C7.95104858 10.59736023 7.95922607 11.47865601 7.96765137 12.38665771 C7.9925563 15.31635853 8.00903428 18.24601074 8.0234375 21.17578125 C8.02876118 22.17383474 8.03408485 23.17188824 8.03956985 24.20018578 C8.06632351 29.48265186 8.08569136 34.76509412 8.10009766 40.04760742 C8.11675165 45.5123506 8.16152952 50.97649141 8.2124691 56.44100666 C8.24607854 60.63513403 8.2576682 64.82911737 8.26332474 69.02336693 C8.27005462 71.03806347 8.28532149 73.05274997 8.30921555 75.06731606 C8.34073522 77.88563114 8.34092384 80.70230786 8.33349609 83.52075195 C8.34990143 84.35571701 8.36630676 85.19068207 8.38320923 86.0509491 C8.34041727 90.01065617 8.16911585 91.86875862 5.40103149 94.79948425 C1.66577253 96.93129809 -1.07976563 97.44996755 -5.3125 97.4375 C-6.62927734 97.44136719 -6.62927734 97.44136719 -7.97265625 97.4453125 C-10.25 97.3125 -10.25 97.3125 -12.25 96.3125 C-12.36577894 84.38637705 -12.45465723 72.46038748 -12.50906086 60.53381729 C-12.53517016 54.99597595 -12.57059311 49.4585187 -12.62719727 43.92089844 C-12.68146864 38.57814502 -12.71141049 33.23576136 -12.72438622 27.8927536 C-12.7336348 25.85292488 -12.75169506 23.81311671 -12.77865028 21.77344513 C-12.81487563 18.91915438 -12.81994806 16.06639718 -12.81762695 13.21191406 C-12.83560333 12.36602722 -12.85357971 11.52014038 -12.87210083 10.64862061 C-12.83571766 6.52188952 -12.80978429 4.92397853 -9.93424988 1.78289795 C-6.44354239 -0.12926722 -3.95788187 -0.12006127 0 0 Z" fill="#529DCC" transform="translate(291.25,10.6875)"/><path d="M0 0 C2.78352771 1.21779337 3.51254181 2.1867725 5 4.875 C5.44901913 7.98464771 5.41826609 11.0507084 5.375 14.1875 C5.38660156 15.01701172 5.39820313 15.84652344 5.41015625 16.70117188 C5.3694083 25.30578149 2.66358605 30.77098332 -3.18359375 37.08203125 C-11.38270563 45.17534813 -21.17996195 45.2214908 -32.125 45.1875 C-33.69314453 45.21166992 -33.69314453 45.21166992 -35.29296875 45.23632812 C-41.28864939 45.24011806 -45.76501748 44.90391265 -51 41.875 C-55.57510356 35.01234467 -54.57924689 23.85682579 -54 15.875 C-53.44034025 13.49272096 -52.74318006 11.21028912 -52 8.875 C-49.06097651 8.74018241 -46.12810441 8.64100584 -43.1875 8.5625 C-41.93743164 8.4996582 -41.93743164 8.4996582 -40.66210938 8.43554688 C-38.34334109 8.38898526 -36.27196694 8.40400698 -34 8.875 C-31.67636697 11.55438304 -31.07718971 13.61770097 -30.0625 17 C-28.87251747 20.21995274 -28.05445898 21.34777051 -25 22.875 C-21.93288436 22.59617131 -20.63629294 21.63252863 -18 19.875 C-17.60959686 17.1841408 -17.60959686 17.1841408 -17.5 14.125 C-16.95662835 10.11462871 -16.68448203 8.44558249 -13.53515625 5.8203125 C-10.73541857 4.34134463 -7.92476 3.08314752 -5 1.875 C-2 -0.125 -2 -0.125 0 0 Z" fill="#559FCD" transform="translate(198,63.125)"/><path d="M0 0 C1.5631897 0.00785522 1.5631897 0.00785522 3.15795898 0.01586914 C4.28266602 0.0190918 5.40737305 0.02231445 6.56616211 0.02563477 C7.75016602 0.03401367 8.93416992 0.04239258 10.15405273 0.05102539 C11.34192383 0.05553711 12.52979492 0.06004883 13.75366211 0.06469727 C16.69967499 0.07652864 19.64558954 0.09301252 22.59155273 0.11352539 C22.70915988 3.27987175 22.77926297 6.44564613 22.84155273 9.61352539 C22.87506836 10.50040039 22.90858398 11.38727539 22.94311523 12.30102539 C23.03621373 18.6317232 21.81495044 22.71483332 18.59155273 28.11352539 C18.05530273 29.24790039 17.51905273 30.38227539 16.96655273 31.55102539 C15.59155273 34.11352539 15.59155273 34.11352539 13.59155273 35.11352539 C10.7078494 35.18547408 7.8491561 35.20644247 4.96655273 35.17602539 C4.16475586 35.17151367 3.36295898 35.16700195 2.53686523 35.16235352 C0.55506267 35.15055707 -1.4267016 35.13262144 -3.40844727 35.11352539 C-3.43309917 30.28971737 -3.45128419 25.46594572 -3.46337891 20.64208984 C-3.468419 18.99983075 -3.47525105 17.35757616 -3.48388672 15.71533203 C-3.49596652 13.3597706 -3.50167865 11.0042683 -3.50610352 8.64868164 C-3.5112648 7.91013443 -3.51642609 7.17158722 -3.52174377 6.41065979 C-3.52193976 4.64454451 -3.47039445 2.87855393 -3.40844727 1.11352539 C-2.40844727 0.11352539 -2.40844727 0.11352539 0 0 Z" fill="#569FCE" transform="translate(148.408447265625,11.886474609375)"/></svg>`;

		const card = $(`
			<div class="vehicle-card" data-vehicle="${vehicle.name}" draggable="true">
				<div class="kanban-plate">
					<div class="kanban-plate-inner">
						<div class="kanban-plate-left">
							${dubai_logo}
							<div class="kanban-plate-code">${plate_code}</div>
						</div>
						<div class="kanban-plate-right">
							<div class="kanban-plate-number">${plate_no}</div>
						</div>
					</div>
				</div>
				<div class="vehicle-meta">
					<div class="model" title="${model_text} ${vehicle.year || ''}">${model_text}</div>
					<div class="detail-row">
						<span class="detail-label">Mileage:</span>
						<span class="detail-value">${mileage}</span>
					</div>
					${links_html ? `<div class="vehicle-links">${links_html}</div>` : ''}
					${period_html}
				</div>
				${alerts_html ? `<div>${alerts_html}</div>` : ''}
			</div>
		`);

		// Handle link clicks to prevent card click from firing
		card.find('.vehicle-links a').on('click', (e) => {
			e.stopPropagation();
			const doctype = $(e.currentTarget).data('doctype');
			const name = $(e.currentTarget).data('name');
			frappe.set_route('Form', doctype, name);
			return false;
		});

		// Click to open vehicle
		card.on('click', (e) => {
			if (!$(e.target).closest('.dragging').length && !$(e.target).closest('.vehicle-links').length) {
				frappe.set_route('Form', 'Vehicle', vehicle.name);
			}
		});

		return card;
	}

	get_alerts(vehicle) {
		const alerts = [];

		if (vehicle.fuel_level && vehicle.fuel_level < 20) {
			alerts.push({ label: 'Low Fuel', class: 'low-fuel' });
		}

		return alerts;
	}

	format_number(num) {
		if (!num) return '0';
		return parseInt(num).toLocaleString();
	}

	setup_drag_drop() {
		const self = this;
		const board = this.wrapper.find('.kanban-board');

		// Set column count CSS variable
		board.css('--column-count', this.statuses.length);

		this.wrapper.find('.vehicle-card').each(function() {
			const card = $(this);

			card.on('dragstart', function(e) {
				card.addClass('dragging');
				// Shrink all columns to fit on screen
				board.addClass('dragging-active');
				e.originalEvent.dataTransfer.setData('text/plain', card.data('vehicle'));
				e.originalEvent.dataTransfer.effectAllowed = 'move';
			});

			card.on('dragend', function() {
				card.removeClass('dragging');
				// Restore column widths
				board.removeClass('dragging-active');
				self.wrapper.find('.kanban-column').removeClass('drag-over');
			});
		});

		this.wrapper.find('.kanban-column').each(function() {
			const column = $(this);
			const status = column.data('status');

			column.on('dragover', function(e) {
				e.preventDefault();
				column.addClass('drag-over');
			});

			column.on('dragleave', function() {
				column.removeClass('drag-over');
			});

			column.on('drop', function(e) {
				e.preventDefault();
				column.removeClass('drag-over');

				const vehicle_name = e.originalEvent.dataTransfer.getData('text/plain');
				const vehicle = self.vehicles.find(v => v.name === vehicle_name);

				if (vehicle && vehicle.status !== status) {
					self.initiate_status_change(vehicle_name, vehicle, status);
				}
			});
		});
	}

	initiate_status_change(vehicle_name, vehicle_data, to_status) {
		const self = this;
		const from_status = vehicle_data.status;

		// First validate the transition
		frappe.call({
			method: 'right_hire.right_hire.doctype.vehicle_status.vehicle_status.validate_status_change',
			args: {
				vehicle: vehicle_name,
				from_status: from_status,
				to_status: to_status
			},
			callback: (r) => {
				if (r.message && r.message.allowed) {
					// Check if movement details are required
					frappe.call({
						method: 'right_hire.right_hire.doctype.vehicle_status.vehicle_status.get_movement_details_required',
						args: {
							from_status: from_status,
							to_status: to_status
						},
						callback: (mov_r) => {
							if (mov_r.message && mov_r.message.requires_movement) {
								// Fetch active agreement for the vehicle
								frappe.call({
									method: 'right_hire.right_hire.doctype.vehicle_status.vehicle_status.get_vehicle_active_agreement',
									args: { vehicle: vehicle_name },
									callback: (agr_r) => {
										const agreement_info = agr_r.message || {};
										// Show movement dialog with agreement info
										self.show_movement_dialog(
											vehicle_name,
											vehicle_data,
											from_status,
											to_status,
											mov_r.message.movement_type,
											mov_r.message.direction,
											r.message.requires_reason,
											agreement_info
										);
									}
								});
							} else if (r.message.requires_reason) {
								// Just show reason dialog
								self.show_reason_dialog(vehicle_name, from_status, to_status);
							} else {
								// Execute directly
								self.execute_status_change(vehicle_name, to_status, {});
							}
						}
					});
				} else {
					frappe.show_alert({
						message: r.message?.error || __('Status change not allowed'),
						indicator: 'red'
					});
					self.refresh();
				}
			},
			error: () => {
				// If validation service not available, proceed anyway
				self.execute_status_change(vehicle_name, to_status, {});
			}
		});
	}

	show_movement_dialog(vehicle_name, vehicle_data, from_status, to_status, movement_type, direction, requires_reason, agreement_info) {
		const self = this;
		agreement_info = agreement_info || {};

		// Create the movement first, then show the actual form in a modal
		frappe.call({
			method: 'right_hire.right_hire.doctype.vehicle_status.vehicle_status.create_draft_movement_for_kanban',
			args: {
				vehicle: vehicle_name,
				from_status: from_status,
				to_status: to_status,
				movement_type: movement_type,
				direction: direction,
				agreement_type: agreement_info.agreement_type || '',
				agreement_no: agreement_info.agreement_no || '',
				customer: agreement_info.customer || ''
			},
			callback: (r) => {
				if (r.message && r.message.name) {
					// Show the actual Movements form in a modal
					self.show_form_modal(r.message.name, vehicle_name, from_status, to_status);
				}
			},
			error: () => {
				frappe.show_alert({message: __('Failed to create movement'), indicator: 'red'});
			}
		});
	}

	show_form_modal(movement_name, vehicle_name, from_status, to_status) {
		const self = this;

		// Add modal styles if not present
		if (!document.getElementById('form-modal-styles')) {
			$(`<style id="form-modal-styles">
				.form-modal-overlay {
					position: fixed;
					top: 0;
					left: 0;
					right: 0;
					bottom: 0;
					background: rgba(0,0,0,0.5);
					z-index: 1050;
					display: flex;
					align-items: center;
					justify-content: center;
				}
				.form-modal-container {
					background: var(--fg-color);
					width: 95%;
					height: 90%;
					max-width: 1400px;
					border-radius: 8px;
					display: flex;
					flex-direction: column;
					box-shadow: 0 10px 40px rgba(0,0,0,0.3);
				}
				.form-modal-header {
					padding: 15px 20px;
					border-bottom: 1px solid var(--border-color);
					display: flex;
					justify-content: space-between;
					align-items: center;
					background: var(--bg-color);
					border-radius: 8px 8px 0 0;
				}
				.form-modal-header h4 {
					margin: 0;
					font-weight: 600;
				}
				.form-modal-header .btn-close-modal {
					font-size: 24px;
					cursor: pointer;
					color: var(--text-muted);
					background: none;
					border: none;
					padding: 0 10px;
				}
				.form-modal-header .btn-close-modal:hover {
					color: var(--text-color);
				}
				.form-modal-body {
					flex: 1;
					overflow: hidden;
					position: relative;
				}
				.form-modal-body iframe {
					width: 100%;
					height: 100%;
					border: none;
				}
				.form-modal-footer {
					padding: 15px 20px;
					border-top: 1px solid var(--border-color);
					display: flex;
					justify-content: flex-end;
					gap: 10px;
					background: var(--bg-color);
					border-radius: 0 0 8px 8px;
				}
			</style>`).appendTo('head');
		}

		// Create modal overlay
		const modal = $(`
			<div class="form-modal-overlay">
				<div class="form-modal-container">
					<div class="form-modal-header">
						<h4>${__('Movement')}: ${movement_name}</h4>
						<div>
							<span class="text-muted mr-3">${from_status} → ${to_status}</span>
							<button class="btn-close-modal" title="${__('Close')}">&times;</button>
						</div>
					</div>
					<div class="form-modal-body">
						<iframe src="/app/movements/${movement_name}?modal=1"></iframe>
					</div>
					<div class="form-modal-footer">
						<button class="btn btn-default btn-cancel-movement">${__('Cancel & Delete')}</button>
						<button class="btn btn-primary btn-confirm-movement">${__('Save & Complete Status Change')}</button>
					</div>
				</div>
			</div>
		`);

		// Handle iframe load - hide the navbar and sidebar in iframe
		modal.find('iframe').on('load', function() {
			try {
				const iframeDoc = this.contentDocument || this.contentWindow.document;
				const $doc = $(iframeDoc);

				// Hide everything except the movements page container
				$doc.find('.navbar, #page-workspace, #page-Workspaces, [id^="page-"]:not([id*="Movements"]), .page-sidebar, [data-page-container] > .page-sidebar, #portal-settings-launcher').hide();

				// Style the movements page container
				$doc.find('#page-Movements, [data-name="Movements"], [data-page-container="Movements"]').css({
					'width': '100%',
					'left': '0',
					'position': 'relative',
					'height': '100%'
				});

				// In page-container, only show form-page
				$doc.find('.page-head, .page-actions, .form-footer').hide();

				// Make container full width and height
				$doc.find('.container.page-body').css({
					'margin-left': '0',
					'max-width': '100%',
					'width': '100%',
					'height': '100%'
				});

				// Make layout full width
				$doc.find('.layout-main').css({'max-width': '100%', 'height': '100%'});
				$doc.find('.layout-main-section').css({'width': '100%', 'max-width': '100%', 'height': '100%'});

				// Hide sidebar
				$doc.find('.layout-side-section, .form-sidebar').hide();

				// Style form-page - full width and height
				$doc.find('.form-page').css({
					'padding': '15px',
					'width': '100%',
					'height': '100%',
					'max-width': '100%'
				});

				// Make form-layout full
				$doc.find('.form-layout').css({
					'max-width': '100%',
					'width': '100%'
				});

				// Hide primary action since we have our own button
				$doc.find('.primary-action').hide();

				// Hide page-form row
				$doc.find('.page-form.row').hide();

				// Add inline style to html and body for full height
				$doc.find('html, body').css({
					'height': '100%',
					'overflow': 'auto',
					'background-color': 'white'
				});

				// Style layout wrapper
				$doc.find('.layout-main-section-wrapper').css({
					'min-width': '0',
					'background-color': 'hsl(0, 0%, 100%)'
				});

			} catch(e) {
				console.log('Could not modify iframe content:', e);
			}
		});

		// Close button
		modal.find('.btn-close-modal').on('click', () => {
			frappe.confirm(
				__('Close without saving? The draft movement will remain.'),
				() => {
					modal.remove();
					self.refresh();
				}
			);
		});

		// Cancel button - delete the movement
		modal.find('.btn-cancel-movement').on('click', () => {
			frappe.confirm(
				__('Cancel and delete this movement?'),
				() => {
					frappe.call({
						method: 'frappe.client.delete',
						args: {
							doctype: 'Movements',
							name: movement_name
						},
						callback: () => {
							modal.remove();
							frappe.show_alert({message: __('Movement cancelled'), indicator: 'orange'});
							self.refresh();
						}
					});
				}
			);
		});

		// Confirm button - save and execute status change
		modal.find('.btn-confirm-movement').on('click', () => {
			// Trigger save in iframe
			try {
				const iframe = modal.find('iframe')[0];
				const iframeWindow = iframe.contentWindow;

				// Call save on the form
				if (iframeWindow.cur_frm) {
					iframeWindow.cur_frm.save().then(() => {
						// Now execute the status change
						self.finalize_status_change(vehicle_name, to_status, movement_name, modal);
					}).catch((err) => {
						frappe.show_alert({message: __('Please fill all required fields'), indicator: 'red'});
					});
				} else {
					// Fallback - just execute status change
					self.finalize_status_change(vehicle_name, to_status, movement_name, modal);
				}
			} catch(e) {
				console.log('Error saving iframe form:', e);
				// Fallback - just execute status change
				self.finalize_status_change(vehicle_name, to_status, movement_name, modal);
			}
		});

		// ESC key to close
		$(document).on('keydown.formmodal', (e) => {
			if (e.key === 'Escape') {
				modal.find('.btn-close-modal').click();
			}
		});

		// Cleanup on modal remove
		modal.on('remove', () => {
			$(document).off('keydown.formmodal');
		});

		$('body').append(modal);
	}

	finalize_status_change(vehicle_name, to_status, movement_name, modal) {
		const self = this;

		frappe.call({
			method: 'right_hire.right_hire.doctype.vehicle_status.vehicle_status.finalize_kanban_status_change',
			args: {
				vehicle: vehicle_name,
				to_status: to_status,
				movement_name: movement_name
			},
			callback: (r) => {
				if (r.message && r.message.success) {
					modal.remove();
					frappe.show_alert({
						message: r.message.message,
						indicator: 'green'
					});
					self.refresh();
				} else {
					frappe.show_alert({
						message: r.message?.error || __('Failed to change status'),
						indicator: 'red'
					});
				}
			},
			error: () => {
				frappe.show_alert({
					message: __('Failed to change status'),
					indicator: 'red'
				});
			}
		});
	}

	show_reason_dialog(vehicle_name, from_status, to_status) {
		const self = this;

		const dialog = new frappe.ui.Dialog({
			title: __('Reason Required'),
			fields: [
				{
					fieldtype: 'Small Text',
					fieldname: 'reason',
					label: __('Reason for changing status from {0} to {1}', [from_status, to_status]),
					reqd: 1
				}
			],
			primary_action_label: __('Confirm'),
			primary_action: (values) => {
				dialog.hide();
				self.execute_status_change(vehicle_name, to_status, values);
			}
		});

		dialog.show();
	}

	execute_status_change(vehicle_name, to_status, values) {
		const self = this;

		frappe.call({
			method: 'right_hire.right_hire.doctype.vehicle_status.vehicle_status.change_vehicle_status',
			args: {
				vehicle: vehicle_name,
				to_status: to_status,
				movement_data: JSON.stringify(values)
			},
			callback: (r) => {
				if (r.message && r.message.success) {
					let message = r.message.message;
					const movement_name = r.message.movement;
					if (movement_name) {
						message += ` (Movement: ${movement_name})`;
					}
					frappe.show_alert({
						message: message,
						indicator: 'green'
					});
					self.refresh();

					// If there's new damage, offer to open the Movement for detailed logging
					if (values.has_new_damage && movement_name) {
						frappe.confirm(
							__('New damage was reported. Would you like to open the Movement record to add detailed damage documentation with photos?'),
							() => {
								frappe.set_route('Form', 'Movements', movement_name);
							},
							() => {
								// User chose not to open - do nothing
							}
						);
					}
				}
			},
			error: (r) => {
				frappe.show_alert({
					message: __('Failed to change status'),
					indicator: 'red'
				});
				self.refresh();
			}
		});
	}
}
