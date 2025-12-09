from odoo import models, fields, api
from odoo.exceptions import ValidationError
from markupsafe import Markup

import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Confirm order and finalize cashback deduction"""
        result = super().action_confirm()

        for order in self:
            cashback_lines = order.order_line.filtered(
                lambda l: 'Cashback' in (l.name or '')
            )

            cashback_amount = abs(sum(cashback_lines.mapped('price_subtotal')))

            if cashback_amount > 0:
                pass

        return result

    def action_cancel(self):
        """Cancel order and restore cashback balance"""
        odoo_bot = self.env.ref('base.partner_root')
        for order in self:
            cashback_lines = order.order_line.filtered(
                lambda l: 'Cashback' in (l.name or '')
            )

            cashback_amount = abs(sum(cashback_lines.mapped('price_subtotal')))

            if cashback_amount > 0 and order.partner_id:
                # Restore cashback balance
                order.partner_id.cashback_balans += cashback_amount

                # Post message to partner chatter
                currency = order.partner_id.company_id.currency_id
                message = Markup(f"""
                           <strong>Cashback Refunded</strong><br/>
                           <ul>
                               <li><strong>Reason:</strong> Sales Order {order.name} was cancelled</li>
                               <li><strong>Refunded Amount:</strong> {cashback_amount:,.2f} {currency.name}</li>
                               <li><strong>New Cashback Balance:</strong> {order.partner_id.cashback_balans:,.2f} {currency.name}</li>
                           </ul>
                           """)

                order.partner_id.message_post(
                    body=message,
                    subject='Cashback Refunded - Order Cancelled',
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    author_id=odoo_bot.id
                )

        return super().action_cancel()

    def action_open_cashback_wizard(self):
        """Open cashback redemption wizard"""
        if not self.partner_id.cashback_balans or self.partner_id.cashback_balans <= 0:
            _logger.info(f'No cashback balance available for {self.partner_id.name} '
                         f'Balance: {self.partner_id.cashback_balans} ')

            raise ValidationError(
                f'Partner {self.partner_id.name} has no available cashback balance'
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Redeem Cashback',
            'res_model': 'cashback.redemption.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            }
        }