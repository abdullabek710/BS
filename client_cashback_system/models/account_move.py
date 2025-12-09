from odoo import models, fields, api
from odoo.exceptions import ValidationError

from datetime import datetime
from markupsafe import Markup
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Post invoice and process cashback"""
        result = super().action_post()

        # Processing cashback after invoice is posted
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund']:
                move._process_cashback_on_invoice()

        return result

    def _process_cashback_on_invoice(self):
        """Process cashback for customer invoices"""
        for move in self:
            if move.move_type == 'out_refund':
                continue

            if not move.partner_id:
                continue

            partner = move.partner_id.commercial_partner_id

            # Checking if cashback is enabled
            cashback_enabled = self.env['ir.config_parameter'].sudo().get_param('cashback.enabled')
            if cashback_enabled != 'True':
                continue

            # Partner's cashback percent
            cashback_precent = partner.cashback_precent or 0
            if cashback_precent <= 0:
                continue

            # Summing up only products with positive price
            positive_price_total = sum(
                line.price_subtotal for line in move.line_ids if line.price_unit > 0
            )
            _logger.info('Positive price total: %f', positive_price_total)


            # Company currency
            company_currency = move.company_id.currency_id

            # Calculating cashback amount in invoice currency
            cashback_amount_invoice_currency = positive_price_total * (cashback_precent / 100)

            # Converting to company currency if needed
            if move.currency_id != company_currency:
                cashback_amount = move.currency_id._convert(
                    cashback_amount_invoice_currency,
                    company_currency,
                    move.company_id,
                    move.date
                )
            else:
                cashback_amount = cashback_amount_invoice_currency

            # Creating cashback transaction and write to chatter
            self._create_cashback_transaction(
                move,
                partner,
                cashback_amount,
                company_currency,
                cashback_precent
            )

    def _create_cashback_transaction(self, move, partner, cashback_amount, currency, percent):
        """Create cashback transaction and log to partner chatter"""

        odoo_bot = self.env.ref('base.partner_root')


        partner.accumulated_cashback += cashback_amount

        message = Markup(f"""
                <strong>Cashback Transaction</strong><br/>
                <ul>
                    <li><strong>Invoice:</strong> {move.name}</li>
                    <li><strong>Invoice Date:</strong> {move.date.strftime('%Y-%m-%d')}</li>
                    <li><strong>Invoice Amount:</strong> {move.amount_total:,.2f} {move.currency_id.name}</li>
                    <li><strong>Cashback Percent:</strong> {percent}%</li>
                    <li><strong>Cashback Amount:</strong> {cashback_amount:,.2f} {currency.name}</li>
                    <li><strong>Total Accumulated Cashback:</strong> {partner.accumulated_cashback:,.2f} {currency.name}</li>
                    <li><strong>Current Cashback Balance:</strong> {partner.cashback_balans:,.2f} {currency.name}</li>
                </ul>
                """)

        partner.message_post(
            body=message,
            subject='Cashback Earned',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=odoo_bot.id,
        )

        move.message_post(
            body=f"Cashback of {cashback_amount:,.2f} {currency.name} ({percent}%) awarded to {partner.name}",
            subject='Cashback Processed',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=odoo_bot.id,
        )

        # Creating cashback record for tracking
        self.env['cashback.transaction'].create({
            'partner_id': partner.id,
            'invoice_id': move.id,
            'cashback_percent': percent,
            'invoice_amount': move.amount_total,
            'invoice_currency_id': move.currency_id.id,
            'cashback_amount': cashback_amount,
            'cashback_currency_id': currency.id,
            'transaction_date': move.date
        })