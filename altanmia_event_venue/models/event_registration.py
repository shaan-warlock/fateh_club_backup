import uuid
import base64
import io
import logging

_logger = logging.getLogger(__name__)

import qrcode
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.tools import format_datetime
from datetime import datetime, timedelta
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.image import image_data_uri, base64_to_image
from pytz import timezone, utc

class EventRegistration(models.Model):
    _name = 'event.registration'
    _inherit = ['event.registration', 'portal.mixin']

    def get_gate(self):
        self = self.sudo()
        for record in self:
            if not record.event_ticket_id or record.sudo().section_id:
                return record.section_id.closet_gate.main_gate
            val = {'state': 'open'}
            _logger.info(">>>>>>Loop in section %s" % record.event_ticket_id.section_ids)
            for section in record.event_ticket_id.section_ids:
                regs_count = self.env['event.registration'].search_count([
                    ('section_id', '=', section.id),
                    ('event_id', '=', record.event_ticket_id.event_id.id),
                    ('state', '=', 'open')
                ])
                _logger.info("@@@@@@@@@ regs_count: %s section.absorptive_capacity: %s Check conditoin: %s" % (regs_count, section.absorptive_capacity, regs_count < section.absorptive_capacity))
                if regs_count < section.absorptive_capacity:
                    return section.closet_gate.main_gate
                    break
            return ''


    def gate_code(self):
        self = self.sudo()
        _logger.info(">>>>>>>>>>>>>>>>>>>>Registration: %s Section: %s Gate Code: %s:" % (self, self.sudo().section_id, self.section_id.closet_gate))
        _logger.info(">>>>>>>>>>>>>>>>>>>>Gate Code: %s:" % self.section_id.closet_gate.code)
        for record in self:
            if not record.event_ticket_id or record.sudo().section_id:
                return record.section_id.closet_gate.code
            val = {'state': 'open'}
            _logger.info(">>>>>>Loop in section %s" % record.event_ticket_id.section_ids)
            for section in record.event_ticket_id.section_ids:
                regs_count = self.env['event.registration'].search_count([
                    ('section_id', '=', section.id),
                    ('event_id', '=', record.event_ticket_id.event_id.id),
                    ('state', '=', 'open')
                ])
                _logger.info("@@@@@@@@@ regs_count: %s section.absorptive_capacity: %s Check conditoin: %s" % (regs_count, section.absorptive_capacity, regs_count < section.absorptive_capacity))
                if regs_count < section.absorptive_capacity:
                    return section.closet_gate.code
                    break
            return ''

    def section_code(self):
        self = self.sudo()
        _logger.info(">>>>>>>>>>>>>>>>>>>>Section Code: %s" % self.section_id.code)
        for record in self:
            if not record.event_ticket_id or record.sudo().section_id:
                return record.section_id.code
            val = {'state': 'open'}
            _logger.info(">>>>>>Loop in section %s" % record.event_ticket_id.section_ids)
            for section in record.event_ticket_id.section_ids:
                regs_count = self.env['event.registration'].search_count([
                    ('section_id', '=', section.id),
                    ('event_id', '=', record.event_ticket_id.event_id.id),
                    ('state', '=', 'open')
                ])
                _logger.info("@@@@@@@@@ regs_count: %s section.absorptive_capacity: %s Check conditoin: %s" % (regs_count, section.absorptive_capacity, regs_count < section.absorptive_capacity))
                if regs_count < section.absorptive_capacity:
                    return section.code
                    break
            return ''

    def _default_access_token(self):
        return str(uuid.uuid4())

    gift_line_id = fields.Many2one('event.gift.line')
    season_ticket_id = fields.Many2one('event.season.ticket')

    section_id = fields.Many2one('event.venue.section')
    section_closset_gate = fields.Char(compute='_compute_related_closset_gate')

    section_map = fields.Binary(string="Section Map", compute="_compute_section_map")

    ref = fields.Char(string="Reference")

    qrcode = fields.Binary(
        attachment=False, string='QRCode', store=True, readonly=True,
        compute='_compute_qrcode',
    )
    qrcode_generate_timestamp = fields.Datetime()

    is_policy_accepted = fields.Boolean('Is Event Policy Accepted')

    price = fields.Float(string='Price', compute='_compute_price')

    access_token = fields.Char('Access Token', default=_default_access_token, readonly=True)

    @api.depends('partner_id.name', 'event_id', 'event_ticket_id')
    def _compute_qrcode(self):
        # utc_date = datetime.now(timezone.utc)
        # utc_date = utc_date.strftime('%Y-%m-%d %H:%M:%S')
        for ticket in self:
            localized_date = utc.localize(datetime.now(), is_dst=False).astimezone(timezone(ticket.event_id.date_tz))

            if ticket.qrcode and ticket.qrcode_generate_timestamp:
                if ticket.qrcode_generate_timestamp + timedelta(minutes=1) > localized_date.replace(tzinfo=None):
                    localized_date = ticket.qrcode_generate_timestamp

            localized_date = localized_date.replace(tzinfo=None)
            info = f"{ticket.id}-{ticket.partner_id.name}-{ticket.event_id.name}-{ticket.event_ticket_id.name}-Date:{str(localized_date)}"
            data = io.BytesIO()
            qrcode.make(info.encode(), box_size=4).save(data, optimise=True, format='PNG')
            ticket.qrcode = base64.b64encode(data.getvalue()).decode()
            ticket.qrcode_generate_timestamp = localized_date

    def get_event_ticket_qrcode(self):
        self.sudo()._compute_qrcode()
        return '/web/image/event.registration/%s/qrcode' % self.id

    def get_event_ticket_qrcode_for_portal(self):
        self.sudo()._compute_qrcode()
        return '/webb/image/event.registration/%s/qrcode' % self.id

    def action_confirm(self):
        for record in self:
            if not record.event_ticket_id:
                continue
            val = {'state': 'open'}
#            _logger.info(">>>>>>Loop in section %s" % record.event_ticket_id.section_ids)
            for section in record.event_ticket_id.section_ids:
                regs_count = self.env['event.registration'].search_count([
                    ('section_id', '=', section.id),
                    ('event_id', '=', record.event_ticket_id.event_id.id),
                    ('state', '=', 'open')
                ])
#                _logger.info("@@@@@@@@@ regs_count: %s section.absorptive_capacity: %s Check conditoin: %s" % (regs_count, section.absorptive_capacity, regs_count < section.absorptive_capacity))
                if regs_count < section.absorptive_capacity:
                    val['section_id'] = section.id
                    break
            self.write(val)

    # def action_send_badge_email(self):
    #     res = super(EventRegistration, self).action_send_badge_email()
    #     reg_id = self.env['event.registration'].sudo().browse(res.get('context').get('default_res_id'))
    #     res.get('context').update({'default_attachment_ids':reg_id.sale_order_id.invoice_ids.attachment_ids[0].ids})
    #     return res

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []  # Create a new list to store modified dictionaries
 
        for vals in vals_list:
            new_vals = dict(vals)  # Create a copy of vals to work with
            new_vals['ref'] = self.env['ir.sequence'].next_by_code('ticket.no')
            new_vals_list.append(new_vals)  # Append the modified dictionary to the new list
        _logger.info("!!!!!!!!!!!!!!!!!!!!!!!%s" % new_vals_list)
        return super().create(new_vals_list)

    def _synchronize_so_line_values(self, so_line):
        if so_line.order_id.season_ticket_id:
            return {}
        return super(EventRegistration, self)._synchronize_so_line_values(so_line)

    @api.depends('event_id')
    def _compute_section_map(self):
        for record in self:
            record = record.sudo()
            sections = record.event_id.venue_id.section_ids

            # Add image in base64 inside the shape.
            uri = image_data_uri(record.event_id.venue_id.sections_background)
            # headers = [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff'),
            #            ('Content-Security-Policy', "default-src 'none'")]

            sections_svg = f"""<?xml version='1.0' encoding='UTF-8'?>
                                <svg style="background-image: url({uri});background-size: cover;" viewBox="0 0 {record.event_id.venue_id.layout_width} {record.event_id.venue_id.layout_high}" xmlns='http://www.w3.org/2000/svg'>
                            """
            for sec in sections:
                section_class = "highlight" if sec.id == record.section_id.id else ''
                section_style = 'style="stroke:#000000; stroke-width:1px; fill:#FF0000; "' if sec.id == record.section_id.id else ''
                sections_svg += f'<path {section_style} class="{section_class}" d="{sec.vector_shape}" fill="{sec.color}"/>'
            sections_svg += "</svg>"
            # record.section_map = record.event_id.venue_id.sections_background
            record.section_map = base64.b64encode(sections_svg.encode())

    def _update_mail_schedulers(self):
        """ Update schedulers to set them as running again, and cron to be called
        as soon as possible. """
        open_registrations = self.filtered(lambda registration: registration.state == 'open')
        open_gift_registrations = self.filtered(lambda registration: registration.state == 'open' and registration.payment_status == "free")
        open_paid_registrations = self.filtered(lambda registration: registration.state == 'open' and registration.payment_status != "free")

        # if open_registrations:
        #     onsubscribe_schedulers = self.env['event.mail'].sudo().search([
        #         ('event_id', 'in', open_registrations.event_id.ids),
        #         ('interval_type', '=', 'after_sub')
        #     ])

        #     if onsubscribe_schedulers:
        #         onsubscribe_schedulers.update({'mail_done': False})
        #         # we could simply call _create_missing_mail_registrations and let cron do their job
        #         # but it currently leads to several delays. We therefore call execute until
        #         # cron triggers are correctly used
        #         onsubscribe_schedulers.with_user(SUPERUSER_ID).execute()

        # if open_gift_registrations:
        #     onsubscribe_gift_schedulers = self.env['event.mail'].sudo().search([
        #         ('event_id', 'in', open_registrations.event_id.ids),
        #         ('interval_type', '=', 'after_gift_confirm')
        #     ])
        #     if onsubscribe_gift_schedulers:
        #         onsubscribe_gift_schedulers.update({'mail_done': False})
        #         onsubscribe_gift_schedulers.with_user(SUPERUSER_ID).execute()

        if open_paid_registrations:
            onsubscribe_paid_schedulers = self.env['event.mail'].sudo().search([
                ('event_id', 'in', open_registrations.event_id.ids),
                ('interval_type', '=', 'after_paid_confirm')
            ])
            if onsubscribe_paid_schedulers:
                onsubscribe_paid_schedulers.update({'mail_done': False})
                onsubscribe_paid_schedulers.with_user(SUPERUSER_ID).execute()

    def _compute_price(self):
        for record in self:
            record.price = round(record.sale_order_line_id.price_total / record.sale_order_line_id.product_uom_qty, 2)
            
    def _check_auto_confirmation(self):
        for reg in self:
            if reg.season_ticket_id:
                return True
        return super(EventRegistration, self)._check_auto_confirmation()

    @api.depends('section_id')
    def _compute_related_closset_gate(self):
        for record in self:
            record.section_closset_gate = record.section_id.closet_gate.name

    # code added by iyad in 2023-09-02
    def register_ticket(self, ticket_id, event_userid):
        try:
            u = self.env['res.users'].sudo().browse(event_userid)
            t = self.env['event.registration'].browse(ticket_id)

            if u.mobile_app != 1 and u.mobile_app != 2:
                return -1
            if len(t) == 0:
                return -2
            if t.state == 'done':
                return -3
            if t.state in ('open') and (u.mobile_app == 2 or (u.id in t.section_id.closet_gate.gate_keepers.ids)):
                t.state = 'done'
                self._cr.commit()
                return 0
            if t.state in ('open') and (
                    u.mobile_app == 1 and (not (u.id in t.section_id.closet_gate.gate_keepers.ids))):
                return -4
            return -5
        except Exception as e:
            return -100

    def load_data(self, event_userid, offset):
        try:
            u = self.env['res.users'].sudo().browse(event_userid)
            if u.mobile_app == 2:
                t = self.env['event.registration'].search_read([('id', '>=', offset)], fields=['id', 'state'])
                return t
            qry = f"""
                        select json_agg(to_json(d))
             from (  SELECT A.id,A.state
            	FROM event_registration A
            	inner join event_venue_section B on A.section_id=B.id
            	inner join event_venue_gate c on  B.closet_gate=c.id
            	inner join event_venue_gate_res_users_rel D on c.id=d.event_venue_gate_id
            	where res_users_id={u.id} and a.id>={offset}
            ) as d
            """
            self._cr.execute(qry)
            t = self._cr.dictfetchall()
            return t[0]["json_agg"]
        except Exception as e:
            return {"error": str(e)}

    def fetch_data(self, data):
        try:
            for rec in data:
                t = self.env['event.registration'].browse(rec['id'])
                if t:
                    t.state = 'done'
                    self._cr.commit()
            return True
        except Exception as e:
            return False

    def fetch_then_load(self, data, event_userid, offset):
        isdone = self.fetch_data(data)
        ret = {}
        if isdone:
            ret = self.load_data(event_userid, offset)
        return ret
    # end code by iy


