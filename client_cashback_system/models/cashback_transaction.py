from odoo import models, fields, api


class CashbackTransaction(models.Model):
    """Model to track all cashback transactions"""
    _name = 'cashback.transaction'
    _description = 'Cashback Transaction'
    _order = 'transaction_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        store=True,
        default=lambda self: self.env.company.currency_id
    )

    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete='cascade')
    cashback_percent = fields.Float(string='Cashback Percent')
    invoice_amount = fields.Float(string='Invoice Amount')
    invoice_currency_id = fields.Many2one('res.currency', string='Invoice Currency')
    cashback_amount = fields.Float(string='Cashback Amount')
    cashback_currency_id = fields.Many2one('res.currency', string='Cashback Currency')
    transaction_date = fields.Date(string='Transaction Date')

    # Status Tracking
    status = fields.Selection(
        [
            ('earned', 'Earned'), # Transaction just created
            ('pending_settlement', 'Pending Settlement'), # Waiting for settlement
            ('settled', 'Settled'), # Successfully transferred to the balance
            ('reset', 'Reset'), # Reversed/refunded
        ],
        string='Status',
        default='earned',
        readonly=True,
    )

    settlement_date = fields.Date(
        string='Settlement Date',
        readonly=True,
        help='Date when cashback was transferred to balance'
    )

    notes = fields.Text(string='Notes')

    def _mark_as_pending_settlement(self):
        """Mark transaction as pending settlement"""
        for transaction in self:
            transaction.status = 'pending_settlement'

    def _mark_as_settled(self):
        """Mark transaction as settled"""
        for transaction in self:
            transaction.status = 'settled'
            transaction.settlement_date = fields.Date.today()

    def _mark_as_refunded(self):
        """Mark transaction as refunded"""
        for transaction in self:
            transaction.status = 'reset'





