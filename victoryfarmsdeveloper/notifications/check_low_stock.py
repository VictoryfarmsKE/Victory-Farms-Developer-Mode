import frappe
from datetime import datetime
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for

@frappe.whitelist()
def check_low_stock():
    item_code = "Cement in 50KG bags"
    warehouse = ""
    
    # Get the current date & time
    now = datetime.now()
    posting_date = now.strftime("%Y-%m-%d")
    posting_time = now.strftime("%H:%M:%S")

    # Fetch stock balance
    stock_data = get_stock_balance_for(item_code, warehouse, posting_date, posting_time)
    
    stock_qty = stock_data.get("qty", 0)

    # frappe.log_error(f"Stock Balance for {item_code}: {stock_qty}")

    if stock_qty <= 100:
        # frappe.log_error(f"Stock is low ({stock_qty}), sending notification...")
        
        # Notify users if stock is low
        recipients = [user.email for user in frappe.get_all("User", filters={"role": "Store Assistant"}, fields=["email"])]

        # frappe.log_error(f"🔔 Notifying users: {recipients}")

        subject = "⚠️ Low Stock Alert: Cement"
        message = f"Cement stock is at {stock_qty} units. Please restock!"
     
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            now=True,
        )
    else:
        frappe.log_error(f"✅ Stock is sufficient ({stock_qty}), no notification needed.")
