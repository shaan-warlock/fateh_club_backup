from odoo import models, fields


class ResUsers(models.Model):

    _inherit = 'res.users'
    mobile_app = fields.Integer(string="Mobile App")


class ResPartner(models.Model):

    _inherit = 'res.partner'
    name = fields.Char(translate=True)
