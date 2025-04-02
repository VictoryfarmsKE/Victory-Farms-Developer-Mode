<p><b>Accounting Period Updated!</b></p>

<p><b>Updated By:</b> {{ doc.modified_by }}</p>

<p>{% if doc.modified %}
    <p><b>Last Modified:</b> {{ frappe.utils.format_datetime(doc.modified, "MMMM dd, yyyy hh:mm") }}</p>
{% endif %}</p>

<p>You can view the record <a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">here</a>.</p>
