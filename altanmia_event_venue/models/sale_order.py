from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tests import tagged, Form
from odoo.osv import expression
import logging
from odoo.addons.website_event_sale.models.sale_order import SaleOrder as WebsiteEventSale
_logger = logging.getLogger(__name__)
# from odoo.tools.misc import formatLang, format_date, get_lang, groupby
from itertools import groupby




class SaleOrder(models.Model):
    _inherit = "sale.order"

    cart_charge_time = fields.Datetime("Cart charge date")
    cart_timer_formatted = fields.Char(compute='_compute_cart_timer_formatted')
    has_event_ticket = fields.Boolean(compute='_compute_has_ticket_event')
    payment_start = fields.Boolean(help="Set True when payment process start, so order cannot be cleared by js timer")

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            user_admin = self.env.ref('base.user_admin')
            import time
            ticket_link_list = []
            registrations = self.env['event.registration'].search([('sale_order_id','=',order.id)])
            registrations = groupby(registrations, key=lambda r: r.phone)
            for phone, tickets in registrations:
                # import pdb;pdb.set_trace()
                for reg in tickets:
                    reg_id = reg
                    # ticket_link += self.env.user.get_base_url() + "/event/registration/view/%s?partnerid=%s\n\n" % (reg_id.access_token, reg_id.partner_id.id) 
                    break
                ticket_link = "https://tickets.fatehclub.com/my/registration"
                try:
                    wizard_dict = reg_id.registration_whatsapp()
                    if isinstance(wizard_dict, dict):
                        wizard_dict['context'].update({'default_free_text_1':ticket_link, 'default_phone':reg_id.phone})
                        wizard = Form(self.env[wizard_dict['res_model']].with_user(user_admin).with_context(wizard_dict['context'])).save()
                        time.sleep(3)
                        wizard.sudo().action_send_whatsapp_template()
                except:
                    return res            
        return res

    @api.depends('cart_charge_time')
    def _compute_cart_timer_formatted(self):
        for order in self:
            time = (fields.Datetime.now() - self.cart_charge_time).seconds if self.cart_charge_time else 0

            if not self.env['ir.config_parameter'].get_param('cart_timeout'):
                order.cart_timer_formatted = None
                continue
            max_time = self.env['ir.config_parameter'].get_param('cart_timeout_amount')

            max_time = (int(max_time) or 10) * 60
            time = max(max_time - time, 0)
            minutes = time // 60
            seconds = time % 60
            order.cart_timer_formatted = f'{minutes:02d}:{seconds:02d}'

    def _compute_has_ticket_event(self):
        for rec in self:
            self.has_event_ticket = any(line.event_ok for line in rec.order_line)

    def check_registration_availability(self):
        for so in self:
            # check ticket availability for each order line that is event product
            for line in so.order_line.filtered('event_ok'):
                line.check_registration_availability()

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def check_registration_availability(self):

        for line in self:
            if line.event_id.seats_limited and line.event_id.seats_max and line.event_id.seats_available < line.product_uom_qty:
                raise UserError(
                    _("Request ticket for event is more than available ticket now. Please get back to the event and readjust the quantity."))

            if line.event_ticket_id.seats_max and line.event_ticket_id.seats_available < line.product_uom_qty:
                raise UserError(
                    _("Request ticket for event is more than available ticket now. Please get back to the event and readjust the quantity."))


def new_cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
    OrderLine = self.env['sale.order.line']
    try:
        if add_qty:
            add_qty = float(add_qty)
    except ValueError:
        add_qty = 1
    try:
        if set_qty:
            set_qty = float(set_qty)
    except ValueError:
        set_qty = 0
        
    if line_id:
        line = OrderLine.browse(line_id)
        ticket = line.event_ticket_id
        old_qty = int(line.product_uom_qty)
        if ticket.id:
            self = self.with_context(event_ticket_id=ticket.id, fixed_price=1)
    else:
        ticket_domain = [('product_id', '=', product_id)]
        if self.env.context.get("event_ticket_id"):
            ticket_domain = expression.AND([ticket_domain, [('id', '=', self.env.context['event_ticket_id'])]])
        ticket = self.env['event.event.ticket'].search(ticket_domain, limit=1)
        old_qty = 0
    new_qty = set_qty if set_qty else (add_qty or 0 + old_qty)

    # case: buying tickets for a sold out ticket
    values = {}
    increased_quantity = new_qty > old_qty
    _logger.info(">>>>>>>>>>>>>>>>>>>Add Quantity: %s" % add_qty)
    _logger.info(">>>>>>>>>>>>>>>>>>>Set Quantity: %s" % set_qty)
    _logger.info(">>>>>>>>>>>>>>>>>>>New Quantity: %s" % new_qty)
    _logger.info(">>>>>>>>>>>>>>>>>>>Old Quantity: %s" % old_qty)
    if ticket and ticket.seats_limited and ticket.seats_available <= 0 and increased_quantity:
        values['warning'] = _('Sorry, The %(ticket)s tickets for the %(event)s event are sold out.') % {
            'ticket': ticket.name,
            'event': ticket.event_id.name}
        # new_qty, set_qty, add_qty = 0, 0, -old_qty
        new_qty, set_qty, add_qty = old_qty, old_qty, 0
    elif line_id and ticket.event_id.max_reserve_ticket and (sum(line.order_id.order_line.mapped('product_uom_qty')) - line.product_uom_qty + new_qty) > ticket.event_id.max_reserve_ticket:
        values['warning'] = _(
            'You cannot reserve tickets on this event more than %s' % ticket.event_id.max_reserve_ticket,
            ticket=ticket.name,
            limit=ticket.max_reserve_ticket,
        )
        new_qty, set_qty, add_qty = old_qty, old_qty, 0
    elif ticket.max_reserve_ticket and new_qty > ticket.max_reserve_ticket:
        values['warning'] = _(
            'Sorry, Reserve limit for %(ticket)s ticket is %(limit)s.',
            ticket=ticket.name,
            limit=ticket.max_reserve_ticket,
        )
        new_qty, set_qty, add_qty = ticket.max_reserve_ticket, ticket.max_reserve_ticket, 0
    # case: buying tickets, too much attendees
    elif ticket and ticket.seats_limited and (new_qty - old_qty) > ticket.seats_available and increased_quantity:
        values['warning'] = _('Sorry, only %(remaining_seats)d seats are still available for the %(ticket)s ticket for the %(event)s event.') % {
            'remaining_seats': ticket.seats_available,
            'ticket': ticket.name,
            'event': ticket.event_id.name}
        # new_qty, set_qty, add_qty = ticket.seats_available, ticket.seats_available, 0
        new_qty, set_qty, add_qty = old_qty, old_qty, 0

    values.update(super(WebsiteEventSale, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs))

    # removing attendees
    if ticket and new_qty < old_qty:
        attendees = self.env['event.registration'].search([
            ('state', '!=', 'cancel'),
            ('sale_order_id', 'in', self.ids),  # To avoid break on multi record set
            ('event_ticket_id', '=', ticket.id),
        ], offset=new_qty, limit=(old_qty - new_qty), order='create_date asc')
        attendees.action_cancel()
        attendees.unlink()
    # adding attendees
    elif ticket and new_qty > old_qty and line_id:
        # do not do anything, attendees will be created at SO confirmation if not given previously
        line._update_registrations(confirm=False, cancel_to_draft=False)

    if self.cart_quantity > 0 and not self.cart_charge_time:
        self.write({'cart_charge_time': fields.Datetime.now()})
    elif not self.cart_quantity or self.cart_quantity == 0:
        self.write({'cart_charge_time': None})
    return values

WebsiteEventSale._cart_update = new_cart_update
