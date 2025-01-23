import datetime
import logging
from collections import defaultdict
from itertools import groupby
import pytz
from odoo.addons.website.controllers.main import QueryURL
from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.osv import expression
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_event.controllers.main import WebsiteEventController
import werkzeug
from odoo.addons.website_sale.controllers.main import WebsiteSale

from odoo.tools import format_datetime

_logger = logging.getLogger(__name__)


class WtWebsite(WebsiteSale):
    @http.route(['/shop/checkout'], type='http', auth="public", website=True, sitemap=False)
    def checkout(self, **post):
        order = request.website.sale_get_order()
        if order:
            request.session['sale_last_order_id'] = order.id
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            return request.redirect('/shop/address')
        redirection = self.checkout_check_address(order)
        if redirection:
            return redirection
        values = self.checkout_values(**post)
        if post.get('express'):
            return request.redirect('/shop/confirm_order')
        values.update({'website_sale_order': order})

        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.redirect('shop/payment')

    def _get_mandatory_fields_billing(self, country_id=False):
        req = ["name", "email","phone" ]#"street", "city", "country_id"
        return req

    def _get_mandatory_fields_shipping(self, country_id=False):
        req = ["name", "email","phone" ]
        return req

#   @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
#   def shop_payment_confirmation(self, **post):
#       sale_order_id = request.session.get('sale_last_order_id')
#       if sale_order_id:
#           order = request.env['sale.order'].sudo().browse(sale_order_id)
#           sale_order_id
#
#
#           lang = 'ar_001'
#           pricelist = request.website.get_current_pricelist()
#           Registration = request.env['event.registration'].with_context(lang=lang).sudo()
#
#           if pricelist:
#               Registration = Registration.with_context(pricelist=pricelist.id)
#
#           registration = Registration.search([('sale_order_id', '=', order.id)], limit=1)
#           if not registration:
#               return super(WtWebsite, self).shop_payment_confirmation(**post)
#               
#           return request.render("altanmia_event_venue.altanmia_event_confirmation", {
#               'order': order,
#               'order_tracking_info': self.order_2_return_dict(order),
#               'registration': registration if registration else False,
#               'event': registration.event_id if registration else False,
#               'lang': lang,
#           })
#       return super(WtWebsite, self).shop_payment_confirmation(**post)

class Event(http.Controller):
    _items_per_page = 12

    @http.route('/event/note', type='json', auth='public', website=True)
    def event_note(self, event_id=None):
        if not event_id:
            return "there is no event instraction"
        event = request.env['event.event'].sudo().browse(int(event_id))
        return event.ticket_instructions

    # backward compatibility
    @http.route(['/web/binary/map'], type='http', auth="public")
    def content_image_backward_compatibility(self, model, id, field,w=None, h=None, **kw):
        venue = request.env['event.venue'].sudo().browse(int(id))
        if not venue:
            return request.not_found()
        width, height = w, h
        if not width:
            width = venue.layout_width if venue.layout_width else 120
            height = venue.layout_high if venue.layout_width else 120

        return request.env['ir.http']._content_image(model=model, res_id=id, field=field, width=width, height=height)


    @http.route('/event/layout', type='json', auth='public', website=True)
    def event_venue_layout(self, venue_id=None):
        if not venue_id:
            return {
                'name': '',
                'location': '',
                'width': 0,
                'high': 0,
                'sections_background': '',
                'sections': [{}]
            }

        venue = request.env['event.venue'].sudo().browse(int(venue_id))
        venue_values = {
            'name': venue.name,
            'location': venue.location,
            'width': venue.layout_width,
            'high': venue.layout_high,
            # 'sections_background': venue.sections_background,
            'sections_background': '/web/binary/map?model=event.venue&field=sections_background&id=' + str(venue.id)+'&w=1200&h=1000',
            'sections': [{
                'id': sec.id,
                'section': sec.name,
                'code': sec.code,
                'vector': sec.vector_shape,
                'color': sec.color,
                'absorptive_capacity': sec.absorptive_capacity,
                'closet_gate': sec.closet_gate.code
            } for sec in venue.section_ids]
        }
        return venue_values

    @http.route(['/event/season/ticket', '/event/season/ticket/page/<int:page>'], type='http',
                auth="public", website=True)
    def event_ticket(self, page=1):
        season_model = request.env['event.season']

        domain = [('date_end', '>', datetime.datetime.now())]
        if not request.env.user.has_group('event.group_event_registration_desk'):
            domain = expression.AND([domain, [('is_published', '=', True)]])

        order = 'date_begin'
        season_count = season_model.search_count(domain)

        pager = portal_pager(
            url="/event/season/ticket",
            url_args={},
            total=season_count,
            page=page,
            step=self._items_per_page
        )
        seasons = season_model.search(domain, order=order, limit=self._items_per_page,
                                                 offset=pager['offset'])

        keep = QueryURL('/event/season/ticket')

        values = {
            'season_tickets': seasons,
            'pager': pager,
            'keep': keep,
            'base_url': '/event/season/ticket'
        }

        return request.render("altanmia_event_venue.season_ticket", values)


    @http.route('/event/season/ticket/<model("event.season"):season>', type='http',
                auth="public", website=True)
    def show_event_ticket(self, season):
        season = season.with_context(pricelist=request.website.id)
        if not request.context.get('pricelist'):
            pricelist = request.website.get_current_pricelist()
            if pricelist:
                season = season.with_context(pricelist=pricelist.id)
        values = {
            'season_ticket': season
        }
        return request.render('altanmia_event_venue.season_ticket_info', values)


    @http.route(['/event/season/ticket/<model("event.season"):season>/buy'], type='json', auth="public", methods=['POST'], website=True)
    def buy_season_ticket(self, season, **post):
        num_tickets = int(post.get('number_of_ticket', 0))
        default_first_attendee = {}
        if not request.env.user._is_public():
            default_first_attendee = {
                "partner_id": request.env.user.partner_id.id,
                "name": request.env.user.name,
                "email": request.env.user.email,
                "phone": request.env.user.mobile or request.env.user.phone,
            }
        else:
            visitor = request.env['website.visitor']._get_visitor_from_request()
            if visitor.email:
                default_first_attendee = {
                    "name": visitor.name,
                    "email": visitor.email,
                    "phone": visitor.mobile,
                    "num_of_tickets": num_tickets
                }
        return request.env['ir.ui.view']._render_template("altanmia_event_venue.season_ticket_buyer_details", {
            'tickets': num_tickets,
            'season_ticket': season,
            'default_first_attendee': default_first_attendee,
            "num_of_tickets": num_tickets
        })

    def _process_buyer_form(self, season, order, form_details):
        buyers = []
        max_index = max(int(key.split('-')[0]) for key in form_details.keys())

        # Iterate over the range of indexes and create a dictionary for each index
        for index in range(max_index + 1):
            item_dict = {}
            for key, value in form_details.items():
                if key.startswith(f"{index}-"):
                    new_key = key[len(f"{index}-"):]  # Remove the index part from the key
                    item_dict[new_key] = value
            item_dict['season_id'] = season.id
            item_dict['sale_order_id'] = order.id
            buyers.append(item_dict)

        return buyers

    @http.route(['''/event/season/ticket/<model("event.season"):season>/buy/confirm'''], type='http', auth="public", methods=['POST'], website=True)
    def buy_season_ticket_confirm(self, season, **post):
        # get website sale order to add season ticket product
        order = request.website.sale_get_order(force_create=1)

        ticket_info = self._process_buyer_form(season, order, post)

        season_tickets = request.env['event.season.ticket'].with_context(create_sale_order=False).sudo().create(ticket_info)

        for ticket in season_tickets:
            cart_values = order.with_context(fixed_price=True)._cart_update(product_id=season.product_id.id, add_qty=1)

        # we have at least one registration linked to a ticket -> sale mode activate
        if season_tickets:
            order = request.website.sale_get_order(force_create=False)
            if order.amount_total:
                return request.redirect("/shop/checkout")
            # free tickets -> order with amount = 0: auto-confirm, no checkout
            elif order:
                order.action_confirm()  # tde notsure: email sending ?
                request.website.sale_reset()

        return request.redirect(('/event/season/ticket/%s/buy/success?' % season.id) + werkzeug.urls.url_encode({'season_ticket_ids': ",".join([str(id) for id in season_tickets.ids])}))

    @http.route(['/event/season/ticket/<model("event.season"):season>/buy/success'], type='http', auth="public", methods=['GET'], website=True, sitemap=False)
    def buy_season_ticket_success(self, event, season_ticket_ids):
        # we don't need this route because all season ticket is salable anb need to rout to check page

        # fetch the related registrations, make sure they belong to the correct visitor / event pair
        visitor = request.env['website.visitor']._get_visitor_from_request()
        # if not visitor:
        #     raise NotFound()
        # attendees_sudo = request.env['event.registration'].sudo().search([
        #     ('id', 'in', [str(registration_id) for registration_id in registration_ids.split(',')]),
        #     ('event_id', '=', event.id),
        #     ('visitor_id', '=', visitor.id),
        # ])
        # return request.render("website_event.registration_complete",
        #     self._get_registration_confirm_values(event, attendees_sudo)

    @http.route(['/event/registration/view/<string:access_token>'], type='http', auth="public", website=True)
    def registration_view(self, access_token, partnerid, state=False, **kwargs):
        lang = 'ar_001'
        my_user = request.env.user
        pricelist = request.website.get_current_pricelist()
        Registration = request.env['event.registration'].with_context(lang=lang).sudo()

        if pricelist:
            Registration = Registration.with_context(pricelist=pricelist.id)
        all_registration = Registration.search([('partner_id', '=', my_user.partner_id.id),('state', '=', 'open')], order="date_open desc")
        registration = Registration.search([('access_token', '=', access_token)], limit=1)
        if registration.id in all_registration.ids:
            idx = all_registration.ids.index(registration.id)
            prev_record = idx != 0 and Registration.browse(all_registration.ids[idx - 1])
            if not prev_record:
                prev_record = Registration.browse(all_registration.ids[-1])
            next_record = idx < len(all_registration.ids) - 1 and Registration.browse(all_registration.ids[idx + 1])
            if not next_record:
                next_record = Registration.browse(all_registration.ids[0])
            current_reg = all_registration.ids.index(registration.id) + 1
            prev_url = "/event/registration/view/%s?partnerid=%s" % (prev_record.access_token, my_user.partner_id.id)
            next_url = "/event/registration/view/%s?partnerid=%s" % (next_record.access_token, my_user.partner_id.id)


            if not registration:
                return request.not_found()
            return request.render("altanmia_event_venue.registration", {
                'registration': registration,
                'event': registration.event_id,
                'lang': lang,
                'all_registration':all_registration,
                'current_reg':current_reg,
                'prev_record':prev_record if prev_record else False,
                'next_record':next_record if next_record else False,
                'partner_id':my_user.partner_id.id,
                'prev_url':prev_url,
                'next_url':next_url,
                'is_mobile': True if kwargs.get('is_mobile', False) else False,
            })
        raise UserError(_("You cannot see other users' tickets!!"))

    @http.route(['/event/<model("event.event"):event>/register'], type='http', auth="public", website=True,
                sitemap=False)
    def event_register(self, event, **post):
        """
        Override the base event register controller to customize functionality.
        """
        values = self._prepare_event_register_values(event, **post)
        return request.render("website_event.event_description_full", values)

    def _prepare_event_register_values(self, event, **post):
        """
        Custom preparation of event register values, adding grouping and sorting logic.
        """

        tickets = request.env['event.event.ticket'].sudo().search([
            ('event_id', '=', event.id),
            ('is_expired', '=', False),
        ])

        sorted_tickets = sorted(tickets, key=lambda ticket: ticket.ticket_label or "")
        tickets_grouped = defaultdict(lambda: defaultdict(list))
        no_group_tickets = []  # Collect all "No Group" tickets here

        for ticket in sorted_tickets:
            if ticket.ticket_label:
                group_key = ticket.ticket_label
                subgroup_key = ticket.name
                tickets_grouped[group_key][subgroup_key].append(ticket)
            else:
                no_group_tickets.append(ticket)

        tickets_grouped = {key: dict(value) for key, value in tickets_grouped.items()}

        urls = event._get_event_resource_urls()
        return {
            'event': event,
            'main_object': event,
            'range': range,
            'google_url': urls.get('google_url'),
            'iCal_url': urls.get('iCal_url'),
            'tickets_grouped': tickets_grouped,
            'no_group_tickets': no_group_tickets,
        }

    @http.route(['/gift_ticket'], type="http", auth='public', website=True)
    def gift_ticket(self, **kw):
        sale_order = request.env['sale.order'].sudo().search([
            ('website_id', '=', request.website.id),
            ('partner_id', '=', request.env.user.partner_id.id),
            ('state', '=', 'sale')
        ], order='create_date desc', limit=1)

        if not sale_order:
            return request.render('altanmia_event_venue.thank_you_page_template', {
                'grouped_products': {},
                'sale_order': None,
            })
        sale_order_lines = sale_order.order_line
        grouped_products = defaultdict(list)
        for line in sale_order_lines:
            if line.product_id:
                grouped_products[line.product_id.id].append(line)
        grouped_products = dict(grouped_products)

        return request.render('altanmia_event_venue.gift_ticket_template', {
            'grouped_products': grouped_products,
            'sale_order': sale_order,
        })

    @http.route(['/gift_ticket/values'], type='http', auth='public', website=True, methods=['POST'])
    def gift_tickets_values(self, **kwargs):
        print("\n\n\n\nkwarg", kwargs)

        return "Form Submitted Successfully!"



