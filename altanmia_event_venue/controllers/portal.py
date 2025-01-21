# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from operator import itemgetter

from odoo import http, _, SUPERUSER_ID
from odoo.http import request
from odoo.osv.expression import AND, OR
from odoo.tools import groupby as groupbyelem
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager

class RegistrationPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if 'registration_count' in counters:
            domain = self._get_portal_default_registration_domain()
            values['registration_count'] = request.env['event.registration'].search_count(domain)

        return values

    def _get_portal_default_registration_domain(self):
        my_user = request.env.user
        return [
            ('state', '=', 'open'),
            ('partner_id', '=', my_user.partner_id.id),
        ]

    def _get_registration_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('all', 'event'):
            search_domain = OR([search_domain, [('event_id.name', 'ilike', search)]])
        return search_domain

    def _registration_get_groupby_mapping(self):
        return {
            'lega': 'event_id.event_type_id',
        }

    @http.route([
        '/my/registration',
        '/my/registration/page/<int:page>',
    ], type='http', auth='user', website=True)
    def portal_my_registration(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kwargs):
        values = self._prepare_portal_layout_values()
        pricelist = request.website.get_current_pricelist()
        Registration = request.env['event.registration']

        if pricelist:
            Registration = Registration.with_context(pricelist=pricelist.id)

        domain = self._get_portal_default_registration_domain()

        searchbar_sortings = {
            'date_open': {'label': _('Date'), 'order': 'date_open desc'},
        }

        searchbar_inputs = {
            'all': {'label': _('Search in All'), 'input': 'all'},
            'event': {'label': _('Search in Event'), 'input': 'event'},
        }

        searchbar_groupby = {
            'none': {'label': _('None'), 'input': 'none'},
            'lega': {'label': _('Lega'), 'input': 'lega'},
        }
        searchbar_groupby={}

        searchbar_filters = {
            'upcoming': {'label': _("Upcoming"), 'domain': [('date_open', '>=', datetime.today())]},
            'past': {'label': _("Past"), 'domain': [('date_open', '<', datetime.today())]},
            'all': {'label': _("All"), 'domain': []},
        }

        if not sortby:
            sortby = 'date_open'
        sort_order = searchbar_sortings[sortby]['order']
        groupby_mapping = self._registration_get_groupby_mapping()
        groupby_field = groupby_mapping.get(groupby, None)
        if groupby_field is not None and groupby_field not in Registration._fields:
            raise ValueError(_("The field '%s' does not exist in the targeted model", groupby_field))
        order = '%s, %s' % (groupby_field, sort_order) if groupby_field else sort_order

        if not filterby:
            filterby = 'all'
        domain = AND([domain, searchbar_filters[filterby]['domain']])

        if search and search_in:
            domain = AND([domain, self._get_registration_search_domain(search_in, search)])

        registration_count = Registration.search_count(domain)

        pager = portal_pager(
            url="/my/registration",
            url_args={'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=registration_count,
            page=page,
            step=self._items_per_page
        )
        registrations = Registration.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        grouped_registrations = False
        # If not False, this will contain a list of tuples (record of groupby, recordset of events):
        # [(res.users(2), calendar.event(1, 2)), (...), ...]
        if groupby_field:
            grouped_registrations = [(g, Registration.concat(*events)) for g, events in groupbyelem(registrations, itemgetter(groupby_field))]

        values.update({
            'registrations': registrations,
            'grouped_registrations': grouped_registrations,
            'page_name': 'registration',
            'pager': pager,
            'default_url': '/my/registration',
            'searchbar_sortings': searchbar_sortings,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'filterby': filterby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': searchbar_filters,
        })
        return request.render("altanmia_event_venue.portal_my_registration", values)

    @http.route(['/my/ticket/print/a5/<string:access_token>'], type='http', auth="public", website=True, sitemap=False)
    def print_ticket_a5(self, access_token, **kwargs):
        lang = 'ar_001'

        pricelist = request.website.get_current_pricelist()
        Registration = request.env.ref('altanmia_event_venue.action_report_a5_registration_v1').with_context(
            lang=lang).sudo()

        registration = request.env['event.registration'].sudo().search([('access_token', '=', access_token)], limit=1)
        if pricelist:
            Registration = Registration.with_context(pricelist=pricelist.id)

        if registration.id:
            pdf, _ = Registration.with_user(SUPERUSER_ID)._render_qweb_pdf(
                [registration.id])
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/my/registration/%s' % registration.id)

    @http.route(['/my/ticket/print/<string:access_token>'], type='http', auth="public", website=True, sitemap=False)
    def print_ticket(self, access_token, **kwargs):
        lang = 'ar_001'

        pricelist = request.website.get_current_pricelist()
        Registration = request.env.ref('altanmia_event_venue.action_report_a4_registration_v2').with_context(lang=lang).sudo()

        registration = request.env['event.registration'].sudo().search([('access_token', '=', access_token)], limit=1)
        if pricelist:
            Registration = Registration.with_context(pricelist=pricelist.id)

        if registration.id:
            pdf, _ = Registration.with_user(SUPERUSER_ID)._render_qweb_pdf(
                [registration.id])
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/my/registration/%s'%registration.id)

    @http.route(['/my/order/ticket/print/<string:access_token>'], type='http', auth="public", website=True, sitemap=False)
    def print_order_ticket(self, access_token, **kwargs):
        lang = 'ar_001'

        pricelist = request.website.get_current_pricelist()
        Registration = request.env.ref('altanmia_event_venue.action_report_a4_registration_v2').with_context(lang=lang).sudo()

        sale_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)

        if not sale_order:
            return request.redirect('/my/orders/')

        registrations = request.env['event.registration'].sudo().search([('sale_order_id', '=', sale_order.id)])
        if pricelist:
            Registration = Registration.with_context(pricelist=pricelist.id)
        if registrations.ids:
            pdf, _ = Registration.with_user(SUPERUSER_ID)._render_qweb_pdf(
                registrations.ids)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/my/orders/%s'%sale_order.id)

    @http.route(['/my/order/ticket/printa/<string:access_token>'], type='http', auth="public", website=True, sitemap=False)
    def printa_order_ticket(self, access_token, **kwargs):
        lang = 'ar_001'

        pricelist = request.website.get_current_pricelist()
        Registration = request.env.ref('altanmia_event_venue.action_report_a5_registration_v1').with_context(lang=lang).sudo()
        sale_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)

        if not sale_order:
            return request.redirect('/my/orders/')

        registrations = request.env['event.registration'].sudo().search([('sale_order_id', '=', sale_order.id)])

        if pricelist:
            Registration = Registration.with_context(pricelist=pricelist.id)

        if registrations.ids:
            pdf, _ = Registration.with_user(SUPERUSER_ID)._render_qweb_pdf(
                registrations.ids)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/my/orders/%s' % sale_order.id)


    @http.route(['/my/ticket/printa/<string:access_token>'], type='http', auth="public", website=True, sitemap=False)
    def printa_ticket(self, access_token, **kwargs):
        lang = 'ar_001'

        pricelist = request.website.get_current_pricelist()
        Registration = request.env.ref('altanmia_event_venue.action_report_a5_registration_v1').with_context(lang=lang).sudo()

        registration = request.env['event.registration'].sudo().search([('access_token', '=', access_token)], limit=1)

        if pricelist:
            Registration = Registration.with_context(pricelist=pricelist.id)

        if registration.id:
            pdf, _ = Registration.with_user(SUPERUSER_ID)._render_qweb_pdf(
                [registration.id])
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/my/registration/%s'%registration.id)

    @http.route(['/webb/image',
    '/webb/image/<string:xmlid>',
    '/webb/image/<string:xmlid>/<string:filename>',
    '/webb/image/<string:xmlid>/<int:width>x<int:height>',
    '/webb/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
    '/webb/image/<string:model>/<int:id>/<string:field>',
    '/webb/image/<string:model>/<int:id>/<string:field>/<string:filename>',
    '/webb/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
    '/webb/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
    '/webb/image/<int:id>',
    '/webb/image/<int:id>/<string:filename>',
    '/webb/image/<int:id>/<int:width>x<int:height>',
    '/webb/image/<int:id>/<int:width>x<int:height>/<string:filename>',
    '/webb/image/<int:id>-<string:unique>',
    '/webb/image/<int:id>-<string:unique>/<string:filename>',
    '/webb/image/<int:id>-<string:unique>/<int:width>x<int:height>',
    '/webb/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>'], type='http', auth="user")
    def contentt_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                      filename_field='name', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None,
                      **kwargs):
        partner = request.env.user.partner_id
        if id:
            ticket = request.env['event.registration'].sudo().browse(id)
            if ticket.partner_id != partner:
                return "You are not allowed to access other tickets"
            return request.env['ir.http']._content_image(xmlid=xmlid, model=model, res_id=id, field=field,
                filename_field=filename_field, unique=unique, filename=filename, mimetype=mimetype,
                download=download, width=width, height=height, crop=crop,
                quality=int(kwargs.get('quality', 0)), access_token=access_token)