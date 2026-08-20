fields = frappe.get_all('Custom Field', filters={'dt': 'Payment Entry'}, fields=['fieldname', 'label', 'fieldtype', 'insert_after'], order_by='idx')
for f in fields:
    if 'beneficiary' in f.fieldname or f.fieldname == 'custom_beneficiaries':
        print(f)
print('---')
print('reference_no field exists:', frappe.db.exists('DocField', {'parent': 'Payment Entry', 'fieldname': 'reference_no'}))
