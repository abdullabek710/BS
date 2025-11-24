from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
	_inherit = 'sale.order'


	def action_confirm(self):
		for order in self:
			partner = order.partner_id

			# Customer Credit Amount
			total_due = partner.credit

			# Customer credit limit
			credit_limit = partner.credit_limit

			amount_company_currency = order.currency_id._convert(
				order.amount_total,
                order.company_id.currency_id,
                order.company_id,
                order.date_order or fields.Date.today()
			)

			_logger.info(f"Amount converted to the companies main currecy: {order.amount_total} Main Currency: {order.company_id}--> {amount_company_currency}")


			new_total_due = total_due + amount_company_currency

			if credit_limit and new_total_due > credit_limit:
				raise UserError(_(
					"Hurmatli foydalanuvchi siz ushbu mijozga %s, o’z qarz limiti %.2f %s dan ortiq sotuv yarata olmaysiz!"
				) % (
					partner.name,
					credit_limit, order.company_id.currency_id.name		
				))
		return super(SaleOrder, self).action_confirm()



