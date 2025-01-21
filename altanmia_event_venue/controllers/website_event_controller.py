
import babel.dates
import pytz
import re
import werkzeug

from ast import literal_eval
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from werkzeug.datastructures import OrderedMultiDict
from werkzeug.exceptions import NotFound
from odoo.addons.phone_validation.tools import phone_validation
from odoo import fields, http, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.http import request
from odoo.tools.misc import get_lang
from odoo.exceptions import UserError



class WebsiteEventControllerInherit(WebsiteEventController):

    @http.route(['/event/check/ticket_quantity'], auth="public", website=True, type="json")
    def check_event_quantity(self, **post):
        order = request.website.sale_get_order()
        ticket_quantity = int(post.get('tv'))
        ticket = request.env['event.event.ticket'].sudo().browse(post.get('ticket_id'))
        total_quantity = sum(order.order_line.filtered(lambda l: l.event_ticket_id.id).mapped('product_uom_qty')) + int(post.get('tv'))
        ticket_line = order.order_line.filtered(lambda l: l.event_ticket_id.id == post.get('ticket_id'))
        
        if ticket_line:
            ticket_quantity += ticket_line.product_uom_qty

        if int(post.get('tv')) > ticket.seats_available:
            return {"success": False, "message": "Reserved ticket not available"}
        elif post.get('max_event_limit') and total_quantity > post.get('max_event_limit'):
            return {"success": False, "message": "Reserved ticket over the limit %s" % post.get('max_event_limit')}
        elif post.get('max_reserve') and ticket_quantity > post.get('max_reserve'):
            return {"success": False, "message": "Reserved ticket over the limit %s" % post.get('max_reserve')}
        else:
            return {"success": True}

    @http.route(['/event/<model("event.event"):event>/registration/new'], auth="public", methods=['POST'],
                website=True)
    def registration_new(self, event, **post):
        tickets = self._process_tickets_form(event, post)
        availability_check = True
        if event.seats_limited:
            ordered_seats = 0
            for ticket in tickets:
                ordered_seats += ticket['quantity']
            if event.seats_available < ordered_seats:
                availability_check = False
        if not tickets:
            return False
        default_first_attendee = {}
        num_of_tickets = []

        for t in tickets:
            if t.get('quantity'):
                num_of_tickets.append(t.get('quantity'))

        if not request.env.user._is_public():
            default_first_attendee = {
                "name": request.env.user.name,
                "email": request.env.user.email,
                "phone": request.env.user.mobile or request.env.user.phone or '',
                "num_of_tickets": num_of_tickets[0]
            }
        else:
            visitor = request.env['website.visitor']._get_visitor_from_request()
            if visitor.email:
                default_first_attendee = {
                    "name": visitor.name,
                    "email": visitor.email,
                    "phone": visitor.mobile or '',
                    "num_of_tickets": num_of_tickets[0]
                }
        return request.env['ir.ui.view']._render_template("website_event.registration_attendee_details", {
            'tickets': tickets,
            'event': event,
            'availability_check': availability_check,
            'default_first_attendee': default_first_attendee,
            "num_of_tickets": num_of_tickets,
            'counter_1': 1
        })

    def _process_tickets_form(self, event, form_details):
        """ Process posted data about ticket order. Generic ticket are supported
        for event without tickets (generic registration).

        :return: list of order per ticket: [{
            'id': if of ticket if any (0 if no ticket),
            'ticket': browse record of ticket if any (None if no ticket),
            'name': ticket name (or generic 'Registration' name if no ticket),
            'quantity': number of registrations for that ticket,
        }, {...}]
        """
        ticket_order = {}
        for key, value in form_details.items():
            registration_items = key.split('nb_register-')
            if len(registration_items) != 2:
                continue
            if value:
                ticket_order[int(registration_items[1])] = int(value)
            else:
                ticket_order[int(registration_items[1])] = 0

        ticket_dict = dict((ticket.id, ticket) for ticket in request.env['event.event.ticket'].sudo().search([
            ('id', 'in', [tid for tid in ticket_order.keys() if tid]),
            ('event_id', '=', event.id)
        ]))

        tickets = [{
            'id': tid if ticket_dict.get(tid) else 0,
            'ticket': ticket_dict.get(tid),
            'name': ticket_dict[tid]['name'] if ticket_dict.get(tid) else _('Registration'),
            'quantity': count,
            # "num_of_tickets":  ticket_order.get('quantity')

        } for tid, count in ticket_dict.items() if count]

        for t in tickets:
            t['quantity'] = ticket_order.get(t['id'])
        return tickets

    def _process_attendees_form(self, event, form_details):
        """ Process data posted from the attendee details form.

        :param form_details: posted data from frontend registration form, like
            {'1-name': 'r', '1-email': 'r@r.com', '1-phone': '', '1-event_ticket_id': '1'}
        """
        # what was done : editing the pop up from showing all the tickets to only showing
        # the groups of tickets, but still this is not enough because we need to modify the pop to
        # allow the duplication of the form as many as the user want
        # the default view of the pop up will only 1 line with

        # TODO:: we need to add a selection field to each line of the pop up it represents
        # the ticket type, then we need to validate the total number of tickets of each type.
        allowed_fields = request.env['event.registration']._get_website_registration_allowed_fields()
        registration_fields = {key: v for key, v in request.env['event.registration']._fields.items() if
                               key in allowed_fields}

        registrations = {}
        global_values = {}
        total_tickets = 0
        data = form_details.items()
        # Convert the data_items list into a dictionary
        data = {}
        indices = {}
        for key, value in form_details.items():
            indices[key.split('-')[0]] = []

        for key, value in form_details.items():
            data[key] = value
            if 'numberOfTickets' in key:
                index = key.split('-')[0]
                value = key.split('-')[1]
                indices[index].append(value)
        # Initialize an empty list to store the transformed data
        result = []
        # Create a mapping of keys in the original data to their corresponding keys in the result.
        key_mapping = {}
        for k in range(int(list(data)[-1][0]) + 1):
            if k == 0:
                continue
            key_mapping.update({
                f'{k}-name': 'name',
                f'{k}-email': 'email',
                f'{k}-phone': 'phone',
                f'{k}-numberOfTickets': 'numberOfTickets',
                f'{k}-event_ticket_id': 'event_ticket_id',
            })
        for i in range(int(list(data)[-1][0]) + 1):
            if i == 0:
                continue
            count = 1
            real_qun = int(data[f'{i}-total_quantity'])
            qun = 0
            for j in indices.get(str(i)):
                key = str(i) + '-numberOfTickets'
                qun += int(data[f'{i}-{j}-numberOfTickets'])
                real_qun -= int(data[f'{i}-{j}-numberOfTickets'])
                phone_code = data.get('phone_code')
                if  "+" in phone_code:
                    phone_code = phone_code.replace("+", "")
                if " " in data[f'{i}-{j}-phone']:
                    web_phone = ''.join(data[f'{i}-{j}-phone'].split(" "))
                else:
                    web_phone = data[f'{i}-{j}-phone']
                if '+' + phone_code in web_phone:
                    phone = ''.join(web_phone.split(" "))
                else:
                    phone = '+' + phone_code + data[f'{i}-{j}-phone']
                if phone_code == '966' or '+966' and data[f'{i}-{j}-phone'][0] == '0':
                    phone = data[f'{i}-{j}-phone'][1:]
                if phone_code == '966' or '+966':
                    phone = data[f'{i}-{j}-phone']
                section_data = {
                    key_mapping[f'{i}-name']: data[f'{i}-{j}-name'],
                    key_mapping[f'{i}-email']: data[f'{i}-{j}-email'],
                    key_mapping[f'{i}-phone']: phone,
                    key_mapping[f'{i}-event_ticket_id']: int(data[f'{i}-{j}-event_ticket_id']),
                }
                # phone_validation.phone_parse(phone, phone_code)
                # Append the section data to the result list, duplicated based on 'numberOfTickets'
                count += 1
                result.extend([section_data.copy()] * int(data[f'{i}-{j}-numberOfTickets']))
            if real_qun < 0:
                raise ValidationError('Cannot distribute tickets with more that you ordered ! ' )


        attendee_tickets = []
        for key, value in form_details.items():
            if '-' in key:
                counter, attr_name = key.split('-', 1)
            else:
                counter = 0
                attr_name = key
            # attr_name = key
            field_name = attr_name.split('-')[0]
            if field_name == 'numberOfTickets':
                if value:
                    # for j in range(value):
                    #     pass
                    total_tickets += int(value)
            # total_tickets += 1


        for key, value in form_details.items():
            if '-' in key:
                x, attr_name = key.split('-', 1)
            else:
                counter = 1
                attr_name = key


        counter = 1
        for i in range(total_tickets):
            for key, value in form_details.items():
                # print('data ', key, value)
                if '-' in key:
                    x, attr_name = key.split('-', 1)
                else:
                    counter = 1
                    attr_name = key
                # attr_name = key
                field_name = attr_name.split('-')[0]
                if field_name not in registration_fields:
                    continue
                elif isinstance(registration_fields[field_name], (fields.Many2one, fields.Integer)):
                    value = int(value) or False  # 0 is considered as a void many2one aka False
                else:
                    value = value
                if str(counter) == '0':
                    global_values[attr_name] = value
                else:
                    registrations.setdefault(str(counter), dict())[attr_name] = value
            # counter += 1
        for key, value in global_values.items():
            for registration in registrations.values():
                registration[key] = value

        return result
