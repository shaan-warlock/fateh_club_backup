# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cart_timeout = fields.Boolean(string='Selling Session Timeout', default=False)
    cart_timeout_amount = fields.Integer(string='Session Timeout', help="Define selling session timeout in minutes", default=10)

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        config_parameters = self.env['ir.config_parameter']
        config_parameters.set_param("cart_timeout", self.cart_timeout)
        config_parameters.set_param("cart_timeout_amount", self.cart_timeout_amount)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        cart_timeout = self.env['ir.config_parameter'].get_param('cart_timeout')
        cart_timeout_amount = self.env['ir.config_parameter'].get_param('cart_timeout_amount')
        if not cart_timeout:
            cart_timeout = False
        if not cart_timeout_amount:
            cart_timeout_amount = 10
        res.update(cart_timeout=cart_timeout, cart_timeout_amount=cart_timeout_amount)

        return res
