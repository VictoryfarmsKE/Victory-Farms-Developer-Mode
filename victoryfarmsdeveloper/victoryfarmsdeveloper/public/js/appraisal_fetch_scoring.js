frappe.ui.form.on('Appraisal', {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__('Fetch Scoring Data'), () => open_fetch_dialog(frm), __('Actions'));
    } else {
      frm.add_custom_button(__('Fetch Scoring Data'), () => open_fetch_dialog(frm));
    }
  }
});

function open_fetch_dialog(frm) {
  const months = [
    'January','February','March','April','May','June','July','August','September','October','November','December'
  ];
  const d = new frappe.ui.Dialog({
    title: __('Fetch Casual Cost (KES per Kg) Scoring'),
    fields: [
      { fieldname: 'month', label: __('Month'), fieldtype: 'Select', options: months.join('\n'), reqd: 1 },
      { fieldname: 'fiscal_year', label: __('Fiscal Year'), fieldtype: 'Link', options: 'Fiscal Year', reqd: 1 },
      { fieldname: 'supplier', label: __('Supplier'), fieldtype: 'Link', options: 'Supplier', default: 'VF Farm Casual Wages' },
      { fieldname: 'department', label: __('Department'), fieldtype: 'Link', options: 'Department', default: 'Processing' },
    ],
    primary_action_label: __('Fetch'),
    primary_action: (values) => {
      d.hide();
      fetch_and_set_appraisal_goal(frm, values);
    }
  });
  d.show();
}

async function fetch_and_set_appraisal_goal(frm, args) {
  try {
    const r = await frappe.call({
      method: 'victoryfarmsdeveloper.victoryfarmsdeveloper.api.fetch_casual_cost_scoring',
      args: {
        month: args.month,
        fiscal_year: args.fiscal_year,
        supplier: args.supplier,
        department: args.department,
      }
    });
    const data = r.message || {};

    // Find the child table field that uses the Appraisal Goal doctype
    const table_df = frm.meta.fields.find(df => df.fieldtype === 'Table' && df.options === 'Appraisal Goal');
    if (!table_df) {
      frappe.msgprint({
        title: __('Not Configured'),
        message: __('This form does not have an Appraisal Goal child table.'),
        indicator: 'orange'
      });
      return;
    }

    // Determine the first non-hidden, non-readonly data-like field in Appraisal Goal
    const child_meta = frappe.get_meta('Appraisal Goal');
    const first_col = child_meta.fields.find(f => !f.hidden && !f.read_only && ['Data','Small Text','Text','Link','Select'].includes(f.fieldtype));
    if (!first_col) {
      frappe.msgprint(__('Could not find a writable column in Appraisal Goal to set.'));
      return;
    }

    // Add or update a row
    const row = frm.add_child(table_df.fieldname);
    // Populate first column with a concise summary as requested
    row[first_col.fieldname] = `Casual Cost/Kg: ${data.casual_costs_per_kg} | Score: ${data.score}`;

    // Optionally, if your child table has known fields, set them here:
    // row.goal = 'Casual Cost (KES per Kg)';
    // row.target = data.casual_costs_per_kg;
    // row.score = data.score;

    frm.refresh_field(table_df.fieldname);
    frappe.show_alert({ message: __('Scoring data added to Appraisal Goal'), indicator: 'green' });
  } catch (e) {
    console.error(e);
    frappe.msgprint({
      title: __('Error'),
      message: e.message || __('Failed to fetch scoring data'),
      indicator: 'red'
    });
  }
}
