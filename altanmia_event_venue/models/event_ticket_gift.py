import base64
import io
import uuid

import qrcode
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.tools import format_datetime
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.image import image_data_uri, base64_to_image

class EventTicketGift(models.Model):
    _name = 'event.gift'
    _description = 'Event Gift'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    gift_line_ids = fields.One2many("event.gift.line", 'gift_id')
    gift_lines_partner_ids = fields.Many2many("res.partner")
    gift_lines_mailing_lists = fields.Many2many("mailing.list")
    partners_mailings = fields.Boolean(compute="_compute_partners_mailings")

    @api.depends('gift_line_ids')
    def _compute_partners_mailings(self):
        for rec in self:
            rec.partners_mailings = False
            if rec.gift_line_ids:
                rec.gift_lines_partner_ids = rec.gift_line_ids.mapped('partner_id')
                rec.gift_lines_mailing_lists = rec.gift_line_ids.mapped('mailing_list_id')

    # event
    event_id = fields.Many2one(
        'event.event', string='Event', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    ticket_count = fields.Integer("Number Of ticket", compute="_compute_num_of_ticket")

    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('open', 'Confirmed'), ('done', 'Attended')],
        string='Status', default='draft', readonly=True, copy=False, tracking=True)

    company_id = fields.Many2one(
        'res.company', string='Company', related='event_id.company_id',
        store=True, readonly=True, states={'draft': [('readonly', False)]})

    active = fields.Boolean(default=True)

    registration_count = fields.Integer(compute='_compute_registration_count')

    def name_get(self):
        ret_list = []
        for gift in self:
            name = f"Gift ticket for {self.event_id.name}"
            ret_list.append((gift.id, name))
        return ret_list

    def _compute_registration_count(self):
        for record in self:
            total = 0
            for line in record.gift_line_ids:
                total += len(line.registration_ids)
            record.registration_count = total

    def _compute_num_of_ticket(self):
        for record in self:
            total = 0
            for gift in record.gift_line_ids:
                total += gift.ticket_count
            record.ticket_count = total

    # ------------------------------------------------------------
    # ACTIONS / BUSINESS
    # ------------------------------------------------------------

    def action_set_draft(self):
        for record in self:
            for line in record.gift_line_ids:
                for reg in line.registration_ids:
                    reg.action_set_draft()
            record.write({'state': 'draft'})

    def action_confirm(self):
        for record in self:
            for line in record.gift_line_ids:
                for reg in line.registration_ids:
                    reg.action_confirm()
            record.write({'state': 'open'})

    def action_set_done(self):
        for record in self:
            for line in record.gift_line_ids:
                for reg in line.registration_ids:
                    reg.action_set_done()
            record.write({'state': 'done'})

    def action_cancel(self):
        for record in self:
            for line in record.gift_line_ids:
                for reg in line.registration_ids:
                    reg.action_cancel()
            record.write({'state': 'cancel'})

    def action_send_badge_email(self):
        for record in self:
            for line in record.gift_line_ids:
                for reg in line.registration_ids:
                    reg.action_send_badge_email()

    def _update_mail_schedulers(self):
        for record in self:
            for line in record.gift_line_ids:
                for reg in line.registration_ids:
                    reg._update_mail_schedulers()

    def action_open_registrations(self):
        """Display the linked registration and adapt the view to the number of records to display."""
        self.ensure_one()
        registrations = self.gift_line_ids.mapped('registration_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("event.action_registration")
        if len(registrations) > 1:
            action['domain'] = [('id', 'in', registrations.ids)]
            tree_view = [(self.env.ref('event.view_event_registration_tree').id, 'tree')]
            if 'views' in action:
                action['views'] = tree_view + [(state,view) for state,view in action['views'] if view != 'tree']
            else:
                action['views'] = tree_view
                
        elif len(registrations) == 1:
            form_view = [(self.env.ref('event.view_event_registration_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = registrations.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        action['context'] = dict(self._context, create=False)
        return action


class EventTicketGiftLine(models.Model):
    _name = 'event.gift.line'
    _description = 'Event Gift Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    event_id = fields.Many2one(related="gift_id.event_id")

    gift_id = fields.Many2one('event.gift')

    state = fields.Selection(related="gift_id.state")

    event_ticket_id = fields.Many2one(
        'event.event.ticket', required=True, string='Event Ticket', ondelete='restrict')

    ticket_count = fields.Integer("Number Of ticket")

    partner_id = fields.Many2one('res.partner', string='Gift To Contact')

    mailing_list_id = fields.Many2one('mailing.list', string='Gift To Mail List')

    @api.onchange('partner_id')
    def onChangePartner(self):
        if self.partner_id:
            self.mailing_list_id = None

    @api.onchange('mailing_list_id')
    def onChangeMailingList(self):
        if self.mailing_list_id:
            self.partner_id = None
            self.ticket_count = self.mailing_list_id.contact_count

    company_id = fields.Many2one(related="gift_id.company_id")

    registration_ids = fields.One2many("event.registration", 'gift_line_id')

    def _check_seat_available(self):
        for record in self:
            if record.event_ticket_id.seats_available < record.ticket_count:
                return False
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            ticket = self.env['event.event.ticket'].browse(val.get('event_ticket_id'))
            if ticket.seats_available < val.get('ticket_count'):
                raise ValidationError(_(f"This number of seat {val.get('ticket_count')} are not available for this event."))

        tickets = super().create(vals_list)

        for ticket in tickets:
            if ticket.mailing_list_id:
                for contact in ticket.mailing_list_id.contact_ids:
                    if contact.phone_mobile_search:
                        phone = contact.phone_mobile_search
                    else:
                        phone = contact.mobile
                    registration_value = {
                        'event_id': ticket.event_id.id,
                        'event_ticket_id': ticket.event_ticket_id.id,
                        'name': contact.name,
                        'phone':phone,
                        'email': contact.email,
                        'company_id': ticket.company_id.id,
                        'state': ticket.state,
                        'gift_line_id': ticket.id,
                        'payment_status': "free",
                    }
                    self.env['event.registration'].create(registration_value)
            elif ticket.partner_id:
                for index in range(ticket.ticket_count):
                    registration_value ={
                        'event_id': ticket.event_id.id,
                        'event_ticket_id': ticket.event_ticket_id.id,
                        'partner_id': ticket.partner_id.id,
                        'company_id': ticket.company_id.id,
                        'state': ticket.state,
                        'gift_line_id': ticket.id
                    }
                    self.env['event.registration'].create(registration_value)
            else:
                raise ValidationError(_("You should select authority, to whom this gift?"))
        return tickets


