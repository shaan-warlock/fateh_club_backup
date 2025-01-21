from odoo.exceptions import AccessError, UserError, ValidationError
from odoo import _, api, fields, models, tools, Command
import logging
from odoo.tools import is_html_empty
from .hijri_converter import Gregorian

_logger = logging.getLogger(__name__)


class EventEvent(models.Model):
    _name = 'event.event'
    _inherit = 'event.event'

    season_ticket_sent = fields.Boolean("Season Ticket Sent", default=False, copy=False)

    # sale_forecast_price_subtotal = fields.Monetary(
    #     string='Forecasted Sale', compute='_compute_forcast_sale_price_subtotal',
    #     groups='sales_team.group_sale_salesman')

    @api.depends('company_id.currency_id',
                 'sale_order_lines_ids.price_subtotal', 'sale_order_lines_ids.currency_id',
                 'sale_order_lines_ids.company_id', 'sale_order_lines_ids.order_id.date_order')
    def _compute_sale_price_subtotal(self):
        """ Takes all the sale.order.lines related to this event and converts amounts
        from the currency of the sale order to the currency of the event company.

        To avoid extra overhead, we use conversion rates as of 'today'.
        Meaning we have a number that can change over time, but using the conversion rates
        at the time of the related sale.order would mean thousands of extra requests as we would
        have to do one conversion per sale.order (and a sale.order is created every time
        we sell a single event ticket). """
        date_now = fields.Datetime.now()
        sale_price_by_event = {}
        if self.ids:
            event_subtotals = self.env['sale.order.line'].read_group(
                [('event_id', 'in', self.ids),
                 ('state', '=','sale'),
                 ('price_subtotal', '!=', 0)],
                ['event_id', 'currency_id', 'price_subtotal:sum'],
                ['event_id', 'currency_id'],
                lazy=False
            )

            company_by_event = {
                event._origin.id or event.id: event.company_id
                for event in self
            }

            currency_by_event = {
                event._origin.id or event.id: event.currency_id
                for event in self
            }

            currency_by_id = {
                currency.id: currency
                for currency in self.env['res.currency'].browse(
                    [event_subtotal['currency_id'][0] for event_subtotal in event_subtotals]
                )
            }

            for event_subtotal in event_subtotals:
                price_subtotal = event_subtotal['price_subtotal']
                event_id = event_subtotal['event_id'][0]
                currency_id = event_subtotal['currency_id'][0]
                sale_price = currency_by_event[event_id]._convert(
                    price_subtotal,
                    currency_by_id[currency_id],
                    company_by_event[event_id],
                    date_now)
                if event_id in sale_price_by_event:
                    sale_price_by_event[event_id] += sale_price
                else:
                    sale_price_by_event[event_id] = sale_price

        for event in self:
            event.sale_price_subtotal = sale_price_by_event.get(event._origin.id or event.id, 0)

    def _default_description(self):
        return self.env['ir.ui.view']._render_template('altanmia_event_venue.event_venue_layout')

    venue_id = fields.Many2one(
        'event.venue', string='Venue',
        tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    first_team = fields.Many2one("event.sport.team", string="First Team", tracking=True)
    second_team = fields.Many2one("event.sport.team", string="second Team", tracking=True)

    date_begin_hijri = fields.Char("Hijri Date", compute="_compute_hijri_date")
    date_begin_hijri_day = fields.Char("Hijri Day", compute="_compute_hijri_date")
    date_begin_day = fields.Char("Begin Day", compute="_compute_hijri_date")

    date_begin_str = fields.Char("Begin Date Str", compute="_compute_hijri_date")
    time_begin_str = fields.Char("Begin Time Str", compute="_compute_hijri_date")

    max_reserve_ticket = fields.Integer("Reserve Limit", help="Default max reserve ticket from website")

    @api.onchange('seats_max')
    def validate_seats_max(self):
        for record in self:
            if record.venue_id and record.seats_max > record.venue_id.absorptive_capacity:
                record.seats_max = record.venue_id.absorptive_capacity
                raise ValidationError(_("The max number of ticket is constraint by venue capacity."))

    def action_send_season_ticket(self):
        for event in self:
            if not event.event_type_id:
                continue
            season_tickets = self.env['event.season.ticket'].search([
                ('event_type_id', '=', event.event_type_id.id),
                ('date_begin', '<', event.date_begin),
                ('date_end', '>', event.date_end)])
            for ticket in season_tickets:
                event_ticket = event.event_ticket_ids.filtered(lambda tic: tic.name == ticket.event_type_ticket_id.name)
                try:
                    order_line = ticket.sale_order_id.order_line[0].id
                except:
                    order_line=None
                registration_value = {
                    'event_id': event.id,
                    'event_ticket_id': event_ticket.id if event_ticket else event.event_ticket_ids.ids[0],
                    'partner_id': ticket.partner_id.id,
                    'name': ticket.name,
                    'email': ticket.email,
                    'phone': ticket.phone,
                    'is_paid': True,
                    'payment_status': "paid",
                    'sale_order_line_id': order_line,
                    'sale_order_id': ticket.sale_order_id.id,
                    'company_id': event.company_id.id,
                    'season_ticket_id': ticket.id
                }
                self.env['event.registration'].create(registration_value)
            event.write({"season_ticket_sent": True})

    # @api.onchange('max_reserve_ticket')
    # def set_max_reserve(self):
    #     for record in self:
    #         for ticket in self.event_ticket_ids:
    #             ticket.max_reserve_ticket = record.max_reserve_ticket

    @api.onchange('first_team', 'second_team')
    def validate_seats_max(self):
        for record in self:
            if record.first_team and record.second_team:
                record.name = f'{record.first_team.name} VS {record.second_team.name}'

    @api.onchange('venue_id')
    def _onchange_venue_id(self):
        if self.venue_id:
            self.seats_limited = True
            self.seats_max = self.venue_id.absorptive_capacity
        else:
            self.seats_limited = False
            self.seats_max = 0

    @api.depends()
    def _compute_hijri_date(self):
        for record in self:
            d = record.date_begin
            if d and d.year and d.month and d.day:
                h = Gregorian(d.year, d.month, d.day).to_hijri()
                record.date_begin_hijri = f" {h.day:02} {h.month_name(language='ar')} {h.year:04} "
                record.date_begin_hijri_day = f"{h.day_name(language='ar')}"
                record.date_begin_day = d.strftime('%A')
                record.date_begin_str = d.strftime('%d %b %Y')
                record.time_begin_str = d.strftime('%I:%M %p')

    @api.depends('venue_id')
    def _compute_seats_max(self):
        for event in self:
            if not event.venue_id:
                event.seats_max = event.seats_max or 0
            else:
                event.seats_max = event.venue_id.absorptive_capacity or 0

    @api.depends('venue_id')
    def _compute_seats_limited(self):
        for event in self:
            if event.venue_id:
                event.seats_limited = True


    def get_phone_formate(self, phone):
        data = {
            'number': '',
            'code': ''
        }
        return data


class EventTicket(models.Model):
    _inherit = 'event.event.ticket'

    section_ids = fields.Many2many("event.venue.section", string="Sections")

    background = fields.Binary(string="Ticket Background")

    background_a4 = fields.Binary(string="Ticket Background A4")

    max_reserve_ticket = fields.Integer("Reserve Limit", help="Max reserve tickets from website")

    label = fields.Char('Label')

    ticket_label = fields.Char(string="Ticket Label")

    @api.onchange('section_ids')
    def _onchange_section_ids(self):
        if self.section_ids:
            total = 0
            for sec in self.section_ids:
                total += sec.absorptive_capacity
            self.seats_max = total
        else:
            self.seats_max = 0

    @api.onchange('seats_max')
    def validate_seats_max(self):
        for record in self:
            sec_capacity = 0
            for sec in self.section_ids:
                sec_capacity += sec.absorptive_capacity
            if 0 < sec_capacity < record.seats_max:
                record.seats_max = sec_capacity
                raise ValidationError(_("The max number of ticket is constraint by section capacity."))

    @api.depends('seats_max', 'registration_ids.state')
    def _compute_seats(self):
        """ Determine reserved, available, reserved but unconfirmed and used seats. """
        # initialize fields to 0 + compute seats availability
        for ticket in self:
            ticket.seats_unconfirmed = ticket.seats_reserved = ticket.seats_used = ticket.seats_available = 0
        # aggregate registrations by ticket and by state
        results = {}
        if self.ids:
            state_field = {
                'draft': 'seats_unconfirmed',
                'open': 'seats_reserved',
                'done': 'seats_used',
            }
            query = """ SELECT event_ticket_id, state, count(event_id)
                        FROM event_registration
                        WHERE event_ticket_id IN %s AND state IN ('draft', 'open', 'done')
                        GROUP BY event_ticket_id, state
                    """
            self.env['event.registration'].flush(['event_id', 'event_ticket_id', 'state'])
            self.env.cr.execute(query, (tuple(self.ids),))
            for event_ticket_id, state, num in self.env.cr.fetchall():
                results.setdefault(event_ticket_id, {})[state_field[state]] = num

        # compute seats_available
        for ticket in self:
            ticket.update(results.get(ticket._origin.id or ticket.id, {}))
            if ticket.seats_max > 0:
                ticket.seats_available = ticket.seats_max - (ticket.seats_reserved + ticket.seats_used + ticket.seats_unconfirmed)


class EventTemplateTicket(models.Model):
    _inherit = 'event.type.ticket'
    background = fields.Binary(string="Ticket Background")


class EventCategory(models.Model):
    _name = "event.category"

    name = fields.Char("Category")


class EventType(models.Model):
    _inherit = 'event.type'

    sponsor_ids = fields.Many2many('event.sponsor', string='Sponsors')
    logo = fields.Image("Logo")
