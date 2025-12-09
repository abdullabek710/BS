from odoo import models, fields, api


class CashbackRedemption(models.Model):
    """Track cashback redemptions"""
    _name = 'cashback.redemption'
    _description = 'Cashback Redemption'
    _order = 'redemption_date desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='cascade'
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        ondelete='cascade'
    )

    redemption_amount = fields.Float(
        string='Redemption Amount',
        required=True,
        readonly=True
    )

    redemption_date = fields.Date(
        string='Redemption Date',
        required=True,
        readonly=True,
        default=fields.Date.today
    )

    notes = fields.Text(string='Notes')

