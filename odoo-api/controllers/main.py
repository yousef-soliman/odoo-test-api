"""Controller for Odoo"""
import logging
from datetime import datetime

from odoo import http
from odoo.http import request
from werkzeug.exceptions import BadRequest, HTTPException

LOGGER = logging.getLogger(__name__)


class RecordNotFound(HTTPException):
    code = 432
    description = "<p>Record Not Found.</p>"
    name = "Record Not Found"


class APIController(http.Controller):
    """API Controller"""

    @http.route(
        "/api/checkpartner",
        type="json",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
        cors="*",
    )
    def check_parnter(self, **payloads):
        """ Check Partner if exists
        :params payloads: json that contains partner name (check swagger)
        :return: json partner id if exists
        :raise: RecordNotFound partner not exists
        :raise: BadRequest Data is inviled
        """
        if not payloads:
            raise BadRequest("The Request should include data")

        partner = payloads.get("partner")
        LOGGER.info("Check Partner Endpoint")
        partner = (
            request.env["res.partner"]
            .sudo()
            .search([("name", "ilike", partner)])
        )
        if not partner:
            raise RecordNotFound("Partner Not Found")
        return {"partner_id": partner.id}

    @http.route(
        "/api/createInvoice",
        type="json",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
        cors="*",
    )
    def create_invoice(self, **payloads):
        """ create invoice 
        :params payloads: json that contains data (check swagger)
        :return: json partner id if exists
        :raise: BadRequest Data is inviled
        :raise: RecordNotFound partner not exists
        :raise: RecordNotFound account not exists
        :raise: RecordNotFound product not exists
        """
        if not payloads:
            raise BadRequest()
        LOGGER.info("Create Invoice Endpoint")
        partner_id = payloads.get("partner_id")
        invoice_date_str = payloads.get("invoice_date")
        invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d %H:%M:%S")
        invoice_model = request.env["account.move"].sudo()
        partner = request.env["res.partner"].sudo().browse(partner_id)
        if not partner:
            raise RecordNotFound("Partner Not Found")
        if not invoice_date:
            raise BadRequest("Invaild invoice date format")

        invoice_lines_values = payloads.get("invoice_lines")
        invoice_line_ids = []
        invoice = invoice_model.create(
            {
                "type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": invoice_date,
            }
        )

        for invoice_line_values in invoice_lines_values:
            try:
                invoice_line_ids += self.create_invoice_line(
                    invoice.id, invoice_line_values
                )
            except Exception as E:
                LOGGER.info(E)
                invoice.unlink()
                raise E

        return {
            "invoice": invoice.id,
        }

    def create_invoice_line(self, invoice_id, vals):
        """ create invoice line
        :params invoice_id: invoice_id
        :params vals: dict of values of invoice line
        :return: json partner id if exists
        :raise: BadRequest Data is inviled
        :raise: RecordNotFound partner not exists
        :raise: RecordNotFound account not exists
        :raise: RecordNotFound product not exists
        """
        invoice_line_model = request.env["account.move.line"].sudo()
        product_id = vals.get("product_id")
        account_id = vals.get("account_id")
        qty = int(vals.get("qty") or 0)
        unit_price = float(vals.get("unit_price") or 0)
        description = vals.get("description") or ""
        product = (
            request.env["product.product"]
            .sudo()
            .search([("id", "=", int(product_id))], limit=1)
        )
        account = (
            request.env["account.account"]
            .sudo()
            .search([("id", "=", int(account_id))], limit=1)
        )
        if not product:
            raise RecordNotFound("Product Not Found")
        if not account:
            raise RecordNotFound("Account Not Found")

        return invoice_line_model.create(
            {
                "product_id": product.id,
                "move_id": invoice_id,
                "account_id": account.id,
                "quantity": qty,
                "price_unit": unit_price,
                "name": description,
            }
        )
