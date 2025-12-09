from odoo import models, fields, api
from odoo.exceptions import ValidationError

from datetime import datetime, timedelta
from markupsafe import Markup

import logging

_logger = logging.getLogger(__name__)

class CashbackRedemptionWizard(models.TransientModel):
    _name = 'cashback.redemption.wizard'
    _description = 'Cashback Redemption Wizard'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        related='sale_order_id.partner_id',
        readonly=True
    )

    cashback_balance = fields.Float(
        string='Available Cashback Balance',
        readonly=True,
        compute='_compute_cashback_balance'
    )

    order_total = fields.Float(
        string='Current Order Total',
        readonly=True,
        compute='_compute_order_total'
    )

    max_redeemable = fields.Float(
        string='Maximum Redeemable',
        readonly=True,
        compute='_compute_max_redeemable',
        help='Minimum of order total and cashback balance'
    )

    redemption_amount = fields.Float(
        string='Redeem Amount',
        required=True,
        help='Amount of cashback to redeem'
    )

    last_redemption_date = fields.Date(
        string='Last Redemption Date',
        readonly=True,
        compute='_compute_last_redemption'
    )

    can_redeem = fields.Boolean(
        string='Can Redeem',
        readonly=True,
        compute='_compute_can_redeem',
        help='Can redeem every 3 months'
    )

    redemption_info = fields.Html(
        string='Redemption Info',
        readonly=True,
        compute='_compute_redemption_info'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('sale_order_id')
    def _compute_cashback_balance(self):
        """Get partner's cashback balance"""
        for wizard in self:
            wizard.cashback_balance = wizard.partner_id.cashback_balans or 0.0

    @api.depends('sale_order_id')
    def _compute_order_total(self):
        """Get current order total"""
        for wizard in self:
            wizard.order_total = wizard.sale_order_id.amount_total or 0.0

    @api.depends('cashback_balance', 'order_total')
    def _compute_max_redeemable(self):
        """Calculate maximum redeemable amount"""
        for wizard in self:
            wizard.max_redeemable = min(wizard.cashback_balance, wizard.order_total)

    @api.depends('partner_id')
    def _compute_last_redemption(self):
        """Get last redemption date"""
        for wizard in self:
            last_redemption = self.env['cashback.redemption'].search(
                [('partner_id', '=', wizard.partner_id.id)],
                order='redemption_date desc',
                limit=1
            )
            wizard.last_redemption_date = last_redemption.redemption_date if last_redemption else None



    @api.depends('last_redemption_date')
    def _compute_can_redeem(self):
        """Check if partner can redeem based on configured days"""
        redeem_days = int(self.env['ir.config_parameter'].sudo().get_param('cashback.redeem_days', default='90'))
        for wizard in self:
            if not wizard.last_redemption_date:
                wizard.can_redeem = True
            else:
                days_since_last = (fields.Date.today() - wizard.last_redemption_date).days
                wizard.can_redeem = days_since_last >= redeem_days

    @api.depends('cashback_balance', 'last_redemption_date', 'can_redeem', 'order_total')
    def _compute_redemption_info(self):
        """Prepare information message"""
        for wizard in self:
            currency = (
                    wizard.partner_id.company_id.currency_id
                    or wizard.sale_order_id.company_id.currency_id
                    or self.env.company.currency_id
            )

            info = f"""
                <div style="padding: 15px; background-color: #f0f0f0; border-radius: 5px;">
                    <h4>Cashback Redemption Information</h4>
                    <table style="width: 100%; margin-top: 10px;">
                        <tr>
                            <td><strong>Available Cashback Balance:</strong></td>
                            <td>{wizard.cashback_balance:,.2f} {currency.name}</td>
                        </tr>
                        <tr>
                            <td><strong>Current Order Total:</strong></td>
                            <td>{wizard.order_total:,.2f} {currency.name}</td>
                        </tr>
                        <tr>
                            <td><strong>Maximum You Can Redeem:</strong></td>
                            <td style="color: green; font-weight: bold;">{wizard.max_redeemable:,.2f} {currency.name}</td>
                        </tr>
                """

            redeem_days = int(self.env['ir.config_parameter'].sudo().get_param('cashback.redeem_days', default='90'))
            if wizard.last_redemption_date:
                days_since = (fields.Date.today() - wizard.last_redemption_date).days
                next_redemption = wizard.last_redemption_date + timedelta(days=redeem_days)

                info += f"""
                        <tr>
                            <td><strong>Last Redemption:</strong></td>
                            <td>{wizard.last_redemption_date.strftime('%Y-%m-%d')}</td>
                        </tr>
                        <tr>
                            <td><strong>Days Since Last Redemption:</strong></td>
                            <td>{days_since} days</td>
                        </tr>
                        <tr>
                            <td><strong>Next Available Redemption:</strong></td>
                            <td>{next_redemption.strftime('%Y-%m-%d')}</td>
                        </tr>
                    """

            if not wizard.can_redeem:
                info += f"""
                        <tr style="background-color: #ffe0e0;">
                            <td colspan="2"><strong style="color: red;">❌ You can only redeem cashback every {redeem_days} days</strong></td>
                        </tr>
                    """
            else:
                info += """
                        <tr style="background-color: #e0ffe0;">
                            <td colspan="2"><strong style="color: green;">✓ You can redeem cashback now</strong></td>
                        </tr>
                    """

            info += """
                    </table>
                </div>
                """

            wizard.redemption_info = info

    @api.onchange('redemption_amount')
    def _onchange_redemption_amount(self):
        """Validate redemption amount"""
        if self.redemption_amount < 0:
            raise ValidationError('Redemption amount cannot be negative')

        if self.redemption_amount > self.max_redeemable:
            raise ValidationError(
                f'Redemption amount cannot exceed {self.max_redeemable:,.2f}'
            )

    def action_redeem_cashback(self):
        """Apply cashback discount to sales order"""
        self.ensure_one()

        odoo_bot = self.env.ref('base.partner_root')

        redeem_days = self.env['ir.config_parameter'].sudo().get_param('cashback.redeem_days', default='90')

        # Validate redemption eligibility
        if not self.can_redeem:
            raise ValidationError('You can only redeem cashback every %s months' % redeem_days)

        if self.redemption_amount <= 0:
            raise ValidationError('Redemption amount must be greater than 0')

        if self.redemption_amount > self.cashback_balance:
            raise ValidationError('Redemption amount exceeds available cashback balance')

        if self.redemption_amount > self.order_total:
            raise ValidationError('Redemption amount cannot exceed order total')

        # Creating cashback product line
        product = self._get_or_create_cashback_product()

        # Add line to sales order
        line_vals = {
            'order_id': self.sale_order_id.id,
            'product_id': product.id,
            'product_uom_qty': 1,
            'price_unit': -self.redemption_amount,  # Negative price
            'name': f'Cashback Redemption - {self.redemption_amount:,.2f}',
        }

        sale_line = self.env['sale.order.line'].create(line_vals)

        self.partner_id.cashback_balans -= self.redemption_amount
        # Creating redemption history
        self.env['cashback.redemption'].create({
            'partner_id': self.partner_id.id,
            'redemption_amount': self.redemption_amount,
            'redemption_date': fields.Date.today(),
            'sale_order_id': self.sale_order_id.id,
        })
        _logger.info("Cashback redemption history created...")

        currency = self.sale_order_id.currency_id
        _logger.info(f"Partner ID: {self.partner_id.id}, Currency: {currency.name}")

        message = Markup(f"""
                <strong>Cashback Redeemed</strong><br/>
                <ul>
                    <li><strong>Redemption Amount:</strong> {self.redemption_amount:,.2f} {currency.name}</li>
                    <li><strong>Applied to Sales Order:</strong> <a href="/web#id={self.sale_order_id.id}&model=sale.order">{self.sale_order_id.name}</a></li>
                    <li><strong>New Cashback Balance:</strong> {self.partner_id.cashback_balans:,.2f} {currency.name}</li>
                    <li><strong>Redemption Date:</strong> {fields.Date.today().strftime('%Y-%m-%d')}</li>
                </ul>
                """)

        self.partner_id.message_post(
            body=message,
            subject='Cashback Redeemed',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id = odoo_bot.id,
        )

        return {'type': 'ir.actions.act_window_close'}

    def _get_or_create_cashback_product(self):
        """Get or create cashback discount product"""
        product = self.env['product.product'].search([
            ('name', '=', 'Cashback'),
            ('type', '=', 'service')
        ], limit=1)

        if not product:
            product = self.env['product.product'].create({
                'name': 'Cashback',
                'type': 'service',
                'list_price': 0,
                'categ_id': self.env.ref('product.product_category_all').id,
            })

        return product

