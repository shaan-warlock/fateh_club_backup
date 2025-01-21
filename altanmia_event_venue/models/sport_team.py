from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class SportTeam(models.Model):
    _name = "event.sport.team"

    _description = 'Event Sport Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Name', index=True, required=True, translate=True)

    logo = fields.Image("Logo")
    active = fields.Boolean(default=True)


class Sponsor(models.Model):
    _name = "event.sponsor"

    _description = 'Event Sponsor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Name', index=True, required=True, translate=True)

    logo = fields.Image("Logo")
    active = fields.Boolean(default=True)