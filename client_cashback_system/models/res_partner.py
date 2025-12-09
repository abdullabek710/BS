from odoo import models, fields, api

from datetime import datetime, timedelta
from markupsafe import Markup

import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'


    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        store=True,
        default=lambda self: self.env.company.currency_id
    )

    cashback_precent = fields.Integer(string="Cashback Precent",
                                      help='Cashback percentage for this contact',
                                      default=lambda self: self._get_default_cashback_percent()
    )

    cashback_balans = fields.Monetary(
        string="Cashback Balans",
        help="Cashback for this contact",
        default=0.0,
        readonly=True,
    )
    accumulated_cashback = fields.Monetary(
        string="Accumulated Cashback",
        help="Cashback for this contact",
        readonly=True,
        default=0.0,
    )

    cashback_enabled = fields.Boolean(
        string="Cashback Enabled",
        compute='_compute_cashback_enabled',
    )

    cashback_transaction_ids = fields.One2many(
        'cashback.transaction',
        'partner_id',
        string="Cashback Transactions",
        readonly=True
    )


    def _compute_cashback_enabled(self):
        """Check if cashback is enabled in settings"""
        cashback_enabled_param = self.env['ir.config_parameter'].sudo().get_param('cashback.enabled')
        is_enabled = cashback_enabled_param == 'True'
        for record in self:
            record.cashback_enabled = is_enabled


    def _get_default_cashback_percent(self):
        """Get default cashback percent from settings"""
        cashback_enabled = self.env['ir.config_parameter'].sudo().get_param('cashback.enabled')
        if cashback_enabled == 'True':
            cashback_percent = self.env['ir.config_parameter'].sudo().get_param('cashback.precent', '0')
            return int(cashback_percent)
        return 0

    # ------------------------#
    # Cashback Monthly Check  #
    # ------------------------#

    def _get_partner_debt(self):
        """Return the total outstanding amount the customer owes."""
        self.ensure_one()
        return self.credit

    def process_end_of_month_cashback(self):
        odoo_bot = self.env.ref('base.partner_root')
        partners = self.search([
            ('cashback_precent', '>', 0),
            ('accumulated_cashback', '>', 0)
        ])

        for partner in partners:
            outstanding_debt = partner._get_partner_debt()

            # Company Main Currency
            if partner.company_id:
                currency = partner.company_id.currency_id
            else:
                currency = self.env.company.currency_id

            _logger.info('Main Company Currency: %s', currency.name)

            current_month_start = fields.Date.today().replace(day=1)
            earned_transactions = self.env['cashback.transaction'].search([
                ('partner_id', '=', partner.id),
                ('status', '=', 'earned'),
                ('transaction_date', '>=', current_month_start)
            ])

            if outstanding_debt == 0:
                # No debt: Transfer accumulated to balance
                partner.cashback_balans += partner.accumulated_cashback

                earned_transactions._mark_as_settled()

                message = Markup(f"""
                            <strong>✓ End of Month Cashback Settlement - Completed</strong><br/>
                            <ul>
                                <li><strong>Settlement Date:</strong> {fields.Date.today().strftime('%Y-%m-%d')}</li>
                                <li><strong>Accumulated Cashback Transferred:</strong> {partner.accumulated_cashback:,.2f} {currency.name}</li>
                                <li><strong>New Cashback Balance:</strong> {partner.cashback_balans + partner.accumulated_cashback:,.2f} {currency.name}</li>
                                <li><strong>Outstanding Invoices:</strong> None</li>
                                <li><strong>Status:</strong> <span style="color: green;"><strong>SETTLED</strong></span></li>
                            </ul>
                            """)
                partner.message_post(
                    body=message,
                    subject='✓ Monthly Cashback Settlement - Completed',
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    author_id = odoo_bot.id,
                )

                # Creating settlement record
                self.env['cashback.transaction'].create({
                    'partner_id': partner.id,
                    'cashback_percent': 0,
                    'invoice_amount': 0,
                    'invoice_currency_id': currency.id,
                    'cashback_amount': partner.accumulated_cashback,
                    'cashback_currency_id': currency.id,
                    'transaction_date': fields.Date.today(),
                    'status': 'settled',
                    'settlement_date': fields.Date.today(),
                    'notes': f'Monthly settlement transfer - No outstanding debt. Accumulated amount transferred to balance.'
                })
                partner.accumulated_cashback = 0

            else:
                earned_transactions._mark_as_refunded()
                message = f"""
                               <strong>⏳ End of Month Cashback Settlement - Reset</strong><br/>
                               <ul>
                                   <li><strong>Settlement Date Attempted:</strong> {fields.Date.today().strftime('%Y-%m-%d')}</li>
                                   <li><strong>Accumulated Cashback (Before):</strong> {partner.accumulated_cashback:,.2f} {currency.name}</li>
                                   <li><strong>Overdue Invoices:</strong> {outstanding_debt:,.2f} {currency.name}</li>
                                   <li><strong>Status:</strong> <span style="color: orange;"><strong>ACCUMULATED CASHBACK SET TO 0</strong></span></li>
                                   <li><strong>Action:</strong> Accumulated cashback has been reset. Once all overdue invoices are paid, pending transactions will be settled.</li>
                               </ul>
                               """
                partner.message_post(
                    body=message,
                    subject='⏳ Monthly Cashback Settlement - Reset',
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    author_id=odoo_bot.id,
                )

                self.env['cashback.transaction'].create({
                    'partner_id': partner.id,
                    'cashback_percent': 0,
                    'invoice_amount': outstanding_debt,
                    'invoice_currency_id': currency.id,
                    'cashback_amount': partner.accumulated_cashback,
                    'cashback_currency_id': currency.id,
                    'transaction_date': fields.Date.today(),
                    'status': 'reset',
                    'notes': f'Monthly settlement pending - Outstanding overdue invoices: {outstanding_debt:,.2f} {currency.name}. Accumulated cashback forfeited due to debt.'
                })

                partner.accumulated_cashback = 0




