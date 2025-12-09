from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cashback_enabled = fields.Boolean(
        string='Cashback Journal',
        config_parameter='cashback.enabled',
        default=False
    )

    cashback_precent = fields.Integer(
        string='Cashback Precent',
        config_parameter='cashback.precent',
        default=0,
        help='Cashback percentage to be applied (e.g., 5 for 5%)'
    )

    cashback_redeem_days = fields.Integer(
        string='Cashback Redeem Days',
        config_parameter='cashback.redeem_days',
        default=0,
        help='Cashback redeem days'
    )

    @api.constrains('cashback_enabled', 'cashback_redeem_days', 'cashback_percent')
    def _check_cashback_required_fields(self):
        """Validate that journal and percent are set when cashback is enabled"""
        for record in self:
            if record.cashback_enabled:
                if record.cashback_redeem_days <= 0:
                    raise ValidationError('Cashback redeem days must be greater than 0')
                if record.cashback_precent <=0:
                    raise ValidationError('Cashback Percentage must be greater than 0 when Cashback is enabled')


    def set_values(self):
        """Save settings and populate cashback percent to all contacts"""
        super().set_values()

        if self.cashback_enabled:
            # Set cashback percent to all existing contacts
            partners = self.env['res.partner'].search([])
            for partner in partners:
                partner.cashback_precent = self.cashback_precent


    @api.onchange('cashback_enabled')
    def _onchange_cashback_enabled(self):
        """Clear cashback fields if disabled"""
        if not self.cashback_enabled:
            self.cashback_precent = 0
            self.cashback_redeem_days = 0
