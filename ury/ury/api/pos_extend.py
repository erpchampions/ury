from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
    SalesInvoice,
    update_multi_mode_option,
)
import frappe
from frappe.utils.nestedset import get_root_of
from frappe.utils import cint
from erpnext.accounts.doctype.pos_invoice.pos_invoice import (
    add_return_modes,
    get_stock_availability,
)
from erpnext.selling.page.point_of_sale.point_of_sale import (
    search_by_term,
    get_conditions,
    get_item_group_condition,
)
from erpnext.accounts.party import get_due_date, get_party_account


@frappe.whitelist()
def overrided_past_order_list(search_term, status, limit=20):
    user = frappe.session.user
    branch_name = None
    room_name = None
    is_restaurant_user = False

    if user != "Administrator":
        sql_query = """
            SELECT b.branch,a.room
            FROM `tabURY User` AS a
            INNER JOIN `tabBranch` AS b ON a.parent = b.name
            WHERE a.user = %s
        """
        branch_array = frappe.db.sql(sql_query, user, as_dict=True)

        if branch_array:
            is_restaurant_user = True
            branch_name = branch_array[0].get("branch")
            room_name = branch_array[0].get("room")

    fields = [
        "name",
        "grand_total",
        "currency",
        "customer",
        "posting_time",
        "posting_date",
        "restaurant_table",
        "invoice_printed",
    ]
    invoice_list = []
    updated_list = []

    if search_term and status:
        # Map "To Bill" to Draft status
        filter_status = "Draft" if status == "To Bill" else status
        
        invoices_by_customer = frappe.get_all(
            "POS Invoice",
            filters={
                "customer": ["like", "%{}%".format(search_term)],
                "status": filter_status,
            },
            fields=fields,
        )
        invoices_by_name = frappe.get_all(
            "POS Invoice",
            filters={"name": ["like", "%{}%".format(search_term)], "status": filter_status},
            fields=fields,
        )
        invoice_list = invoices_by_customer + invoices_by_name
        
        # Apply To Bill filtering if needed
        if status == "To Bill":
            invoice_list = [inv for inv in invoice_list if inv.restaurant_table and inv.invoice_printed == 0]
        
        return invoice_list

    elif status:
        if user != "Administrator" and is_restaurant_user:
            if status == "To Bill":
                invoice_list = frappe.get_all(
                    "POS Invoice",
                    filters={"status": "Draft", "branch": branch_name, "custom_restaurant_room": room_name},
                    fields=fields,
                )
                for invoice in invoice_list:
                    if invoice.restaurant_table and invoice.invoice_printed == 0:
                        updated_list.append(invoice)

            elif status in ["Paid", "Consolidated", "Return"]:
                # Don't filter by branch/room for completed invoices
                invoice_list = frappe.get_all(
                    "POS Invoice",
                    filters={"status": status},
                    fields=fields,
                )
                updated_list = invoice_list

            else:
                invoice_list = frappe.get_all(
                    "POS Invoice",
                    filters={"status": status, "branch": branch_name, "custom_restaurant_room": room_name},
                    fields=fields,
                )
                for invoice in invoice_list:
                    if not invoice.restaurant_table or invoice.invoice_printed == 1:
                        updated_list.append(invoice)

        else:
            if status == "To Bill":
                invoice_list = frappe.get_all(
                    "POS Invoice",
                    filters={"status": "Draft"},
                    fields=fields,
                )
                for invoice in invoice_list:
                    if invoice.restaurant_table and invoice.invoice_printed == 0:
                        updated_list.append(invoice)

            else:
                invoice_list = frappe.get_all(
                    "POS Invoice",
                    filters={"status": status},
                    fields=fields,
                )
                for invoice in invoice_list:
                    if not invoice.restaurant_table or invoice.invoice_printed == 1:
                        updated_list.append(invoice)

    return updated_list