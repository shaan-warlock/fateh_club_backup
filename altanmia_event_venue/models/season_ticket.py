import json

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo import _, api, fields, models, tools
import logging
from odoo.addons.base.models.res_partner import _tz_get
from odoo.tools import format_datetime
import datetime

_logger = logging.getLogger(__name__)


class EventSeason(models.Model):
    _name = 'event.season'
    _description = ''
    _inherit = [
        'website.seo.metadata',
        'website.published.multi.mixin',
        'website.cover_properties.mixin',
        'website.searchable.mixin',
        'mail.thread',
        'mail.activity.mixin'
    ]

    def name_get(self):
        ret_list = []
        for ticket in self:
            name = f"{ticket.event_type_id.name} ({ticket.year})"
            ret_list.append((ticket.id, name))
        return ret_list

    def _default_cover_properties(self):
        res = super()._default_cover_properties()
        res.update({
            'background-image': "url('/altanmia_event_venue/static/src/img/event_cover_4.jpg')",
            'opacity': '0.4',
            'resize_class': 'cover_auto'
        })
        return res

    def _get_selection(self):
        current_year = datetime.datetime.now().year
        return [(str(i), i) for i in range(current_year, current_year + 10)]

    year = fields.Selection(
        selection='_get_selection', string='Year', required=True,
        default=lambda x: str(datetime.datetime.now().year))

    event_type_id = fields.Many2one('event.type', string='Event Template', required=True)
    event_type_ticket_id = fields.Many2one('event.type.ticket', string='Ticket', required=True)

    active = fields.Boolean(default=True)

    # Date fields
    date_tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        compute='_compute_date_tz', readonly=False, store=True)
    date_begin = fields.Datetime(string='Start Date', required=True, tracking=True)
    date_end = fields.Datetime(string='End Date', required=True, tracking=True)
    date_begin_located = fields.Char(string='Start Date Located', compute='_compute_date_begin_tz')
    date_end_located = fields.Char(string='End Date Located', compute='_compute_date_end_tz')
    # product
    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        domain=[("detailed_type", "=", "service")])

    is_published = fields.Boolean(
        string='Published to Wibsite', default=False,  # force None to avoid default computation from mixin
        readonly=False, store=True)

    description = fields.Html(
        string="Description", help="The description shown in the Season Ticket in website")

    price = fields.Float(
        string='Price', compute='_compute_price',
        digits='Product Price', readonly=False, store=True)

    price_reduce = fields.Float(
        string="Price Reduce", compute="_compute_price_reduce",
        compute_sudo=True, digits='Product Price')

    company_id = fields.Many2one(
        'res.company', string='Company', change_default=True,
        default=lambda self: self.env.company,
        required=False)

    @api.depends('product_id')
    def _compute_price(self):
        for ticket in self:
            if ticket.product_id and ticket.product_id.lst_price:
                ticket.price = ticket.product_id.lst_price or 0
            elif not ticket.price:
                ticket.price = 0

    @api.depends('product_id', 'price')
    def _compute_price_reduce(self):
        for ticket in self:
            product = ticket.product_id
            discount = (product.lst_price - product.price) / product.lst_price if product.lst_price else 0.0
            ticket.price_reduce = (1.0 - discount) * ticket.price


    @api.onchange('event_type_id')
    def _onchange_event_type_id(self):
        for rec in self:
            rec.event_type_ticket_id = False

    @api.depends('event_type_id')
    def _compute_date_tz(self):
        for ticket in self:
            if ticket.event_type_id.default_timezone:
                ticket.date_tz = ticket.event_type_id.default_timezone
            if not ticket.date_tz:
                ticket.date_tz = self.env.user.tz or 'UTC'

    @api.depends('date_tz', 'date_begin')
    def _compute_date_begin_tz(self):
        for ticket in self:
            if ticket.date_begin:
                ticket.date_begin_located = format_datetime(
                    self.env, ticket.date_begin, tz=ticket.date_tz, dt_format='medium')
            else:
                ticket.date_begin_located = False

    @api.depends('date_tz', 'date_end')
    def _compute_date_end_tz(self):
        for ticket in self:
            if ticket.date_end:
                ticket.date_end_located = format_datetime(
                    self.env, ticket.date_end, tz=ticket.date_tz, dt_format='medium')
            else:
                ticket.date_end_located = False

    def _default_website_meta(self):
        res = super()._default_website_meta()
        event_cover_properties = json.loads(self.cover_properties)
        # background-image might contain single quotes eg `url('/my/url')`
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = event_cover_properties.get('background-image', 'none')[4:-1].strip("'")
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.display_name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.description
        res['default_twitter']['twitter:card'] = 'summary'
        res['default_meta_description'] = self.description
        return res


class EventSeasonTicket(models.Model):
    _name = 'event.season.ticket'
    _description = ''
    _inherit = ['mail.thread', 'mail.activity.mixin']

    season_id = fields.Many2one('event.season', string="Season", required=True)

    event_type_id = fields.Many2one(related="season_id.event_type_id", string='Event Template', readonly=True)
    event_type_ticket_id = fields.Many2one(related="season_id.event_type_ticket_id", string='Ticket', readonly=True)

    active = fields.Boolean(default=True)

    # Date fields
    date_tz = fields.Selection(related="season_id.date_tz", readonly=True)
    date_begin = fields.Datetime(related="season_id.date_begin", readonly=True)
    date_end = fields.Datetime(related="season_id.date_end", readonly=True)
    date_begin_located = fields.Char(string='Start Date Located', related="season_id.date_begin_located", readonly=True)
    date_end_located = fields.Char(string='End Date Located', related="season_id.date_begin_located", readonly=True)

    partner_id = fields.Many2one('res.partner', string='Client')
    name = fields.Char(
        string='Ticket Owner', index=True,
        compute='_compute_name', readonly=False, store=True, tracking=10)
    email = fields.Char(string='Email', compute='_compute_email', readonly=False, store=True, tracking=11)
    phone = fields.Char(string='Phone', compute='_compute_phone', readonly=False, store=True, tracking=12)
    mobile = fields.Char(string='Mobile', compute='_compute_mobile', readonly=False, store=True, tracking=13)

    # product
    product_id = fields.Many2one(related="season_id.product_id", readonly=True)

    sale_order_id = fields.Many2one('sale.order', string='Sales Order', ondelete='cascade', copy=False)

    registration_count = fields.Integer(compute='_compute_registration_count')

    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('open', 'Confirmed')],
        string='Status', default='draft', readonly=True, copy=False, tracking=True)

    def _compute_registration_count(self):
        for record in self:
            record.registration_count = self.env['event.registration'].search_count([('season_ticket_id', '=', record.id)])

    @api.depends('partner_id')
    def _compute_name(self):
        for ticket in self:
            if not ticket.name and ticket.partner_id:
                ticket.name = ticket._synchronize_partner_values(
                    ticket.partner_id,
                    fnames=['name']
                ).get('name') or False

    @api.depends('partner_id')
    def _compute_email(self):
        for ticket in self:
            if not ticket.email and ticket.partner_id:
                ticket.email = ticket._synchronize_partner_values(
                    ticket.partner_id,
                    fnames=['email']
                ).get('email') or False

    @api.depends('partner_id')
    def _compute_phone(self):
        for ticket in self:
            if not ticket.phone and ticket.partner_id:
                ticket.phone = ticket._synchronize_partner_values(
                    ticket.partner_id,
                    fnames=['phone']
                ).get('phone') or False

    @api.depends('partner_id')
    def _compute_mobile(self):
        for ticket in self:
            if not ticket.mobile and ticket.partner_id:
                ticket.mobile = ticket._synchronize_partner_values(
                    ticket.partner_id,
                    fnames=['mobile']
                ).get('mobile') or False

    def _synchronize_partner_values(self, partner, fnames=None):
        if fnames is None:
            fnames = ['name', 'email', 'phone', 'mobile']
        if partner:
            contact_id = partner.address_get().get('contact', False)
            if contact_id:
                contact = self.env['res.partner'].browse(contact_id)
                return dict((fname, contact[fname]) for fname in fnames if contact[fname])
        return {}

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)

        for ticket in tickets:
            if ticket.partner_id and self.env.context.get('create_sale_order', True):
                sale_order = self.env['sale.order'].create({
                    'partner_id': ticket.partner_id.id,
                    'order_line': [(0, 0, {
                        'product_id': ticket.product_id.id,
                        'product_uom_qty': 1,
                    })],
                })
                ticket.write({'sale_order_id': sale_order.id})

        return tickets

    def action_view_sale_order(self):
        self.sale_order_id.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        return action

    def action_open_registrations(self):
        """Display the linked registration and adapt the view to the number of records to display."""
        self.ensure_one()
        registrations = self.env['event.registration'].search([('season_ticket_id', '=', self.id)])
        action = self.env["ir.actions.actions"]._for_xml_id("event.action_registration")
        if len(registrations) > 1:
            action['domain'] = [('id', 'in', registrations.ids)]
            tree_view = [(self.env.ref('event.view_event_registration_tree').id, 'tree')]
            if 'views' in action:
                action['views'] = tree_view + [(state, view) for state, view in action['views'] if view != 'tree']
            else:
                action['views'] = tree_view

        elif len(registrations) == 1:
            form_view = [(self.env.ref('event.view_event_registration_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = registrations.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        action['context'] = dict(self._context, create=False)
        return action

    def action_set_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            record.sudo().sale_order_id.action_draft()

    def action_confirm(self):
        for record in self:
            record.write({'state': 'open'})
            if record.sale_order_id:
                record.sudo().sale_order_id.action_confirm()


class SaleOrder(models.Model):
    _inherit = "sale.order"

    season_ticket_id = fields.One2many('event.season.ticket', 'sale_order_id', string='Season ticket')