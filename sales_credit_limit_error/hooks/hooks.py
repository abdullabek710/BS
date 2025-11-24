from odoo import api, SUPERUSER_ID

def enable_credit_limit(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].sudo().set_param('account.use_credit_limit', True)