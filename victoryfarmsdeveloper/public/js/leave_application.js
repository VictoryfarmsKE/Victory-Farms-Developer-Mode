// Override the original leave_application_dashboard template
frappe.templates["leave_application_dashboard"] = `
{% if not jQuery.isEmptyObject(data) %}
<table class="table table-bordered small">
	<thead>
		<tr>
			<th style="width:  14%">{{ __("Leave Type") }}</th>
			<th style="width: 14%" class="text-right">{{ __("Yearly Allocated Leave") }}</th>
			<th style="width: 14%" class="text-right">{{ __("Expired Leaves") }}</th>
			<th style="width: 14%" class="text-right">{{ __("Used Leaves") }}</th>
			<th style="width: 14%" class="text-right">{{ __("Leaves Pending Approval") }}</th>
			<th style="width:  14%" class="text-right">{{ __("Available Leaves") }}</th>
		</tr>
	</thead>
	<tbody>
		{% for(const [key, value] of Object.entries(data)) { %}
			{% let color = cint(value["remaining_leaves"]) > 0 ? "green" : "red" %}
			{% 
				const annualLeaveAllocation = {
					"Annual Leave": 21,
					"Annual Leave C&D Level": 28,
					"Maternity Leave": 90,
					"Paternity Leave": 14,
					"Long Weekend": "2/month",
					"Sick Leave - Full Days": 7,
					"Sick Leave - Half Days": 7
				};
				let annualAllocation = annualLeaveAllocation[key] !== undefined ? annualLeaveAllocation[key] : "";
			%}
			<tr>
				<td> {%= key %} </td>
				<td class="text-right"> {%= annualAllocation %} </td>
				<td class="text-right"> {%= value["expired_leaves"] %} </td>
				<td class="text-right"> {%= value["leaves_taken"] %} </td>
				<td class="text-right"> {%= value["leaves_pending_approval"] %} </td>
				<td class="text-right" style="color: {{ color }}"> {%= value["remaining_leaves"] %} </td>
			</tr>
		{% } %}
	</tbody>
</table>
{% else %}
<p style="margin-top: 30px;"> {{ __("No leaves have been allocated.") }} </p>
{% endif %}
`;
