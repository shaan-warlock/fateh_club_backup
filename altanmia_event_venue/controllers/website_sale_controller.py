from odoo import fields, http, SUPERUSER_ID, tools, _

from odoo.addons.website_sale.controllers.main import WebsiteSale, PaymentPortal

from odoo.http import request

from odoo.exceptions import ValidationError
from werkzeug.exceptions import Forbidden, NotFound


class WebsiteSaleInherit(WebsiteSale):

    def checkout_check_address(self, order):
        billing_fields_required = self._get_mandatory_fields_billing(order.partner_id.country_id.id)
        if not all(order.partner_id.read(billing_fields_required)[0].values()):
            return request.redirect('/shop/address?partner_id=%d' % order.partner_id.id)

        shipping_fields_required = self._get_mandatory_fields_shipping(order.partner_shipping_id.country_id.id)
        if not all(order.partner_shipping_id.read(shipping_fields_required)[0].values()):
            return request.redirect('/shop/address?partner_id=%d' % order.partner_shipping_id.id)

    def checkout_form_validate(self, mode, all_form_values, data):
        # mode: tuple ('new|edit', 'billing|shipping')
        # all_form_values: all values before preprocess
        # data: values after preprocess
        error = dict()
        error_message = []

        # Required fields from form
        required_fields = [f for f in (all_form_values.get('field_required') or '').split(',') if f]
        # Required fields from mandatory field function
        country_id = int(data.get('country_id', False))
        # error message for empty required fields
        for field_name in required_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # vat validation
        Partner = request.env['res.partner']
        if data.get("vat") and hasattr(Partner, "check_vat"):
            if country_id:
                data["vat"] = Partner.fix_eu_vat_number(country_id, data.get("vat"))
            partner_dummy = Partner.new(self._get_vat_validation_fields(data))
            try:
                partner_dummy.check_vat()
            except ValidationError as exception:
                error["vat"] = 'error'
                error_message.append(exception.args[0])

        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))
        required_fields = ['phone', 'name']
        return error, error_message

    @http.route('/sale/cart/clear', type='json', auth='public', website=True)
    def sale_clear_cart(self, venue_id=None):
        order = request.website.sale_get_order()
        if order.payment_start:
            return False
        # clear all order line
        order.write({
            'order_line': [(5, 0, 0)],
            'cart_charge_time': None
        })
        return True

    @http.route()
    def cart(self, access_token=None, revive='', **post):
        """
        Main cart management + abandoned cart revival
        access_token: Abandoned cart SO access token
        revive: Revival method when abandoned cart. Can be 'merge' or 'squash'
        """

        order = request.website.sale_get_order()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        order.payment_start = False
        values = {}
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)
            if not abandoned_order:  # wrong token (or SO has been deleted)
                raise NotFound()
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            elif revive == 'squash' or (revive == 'merge' and not request.session.get(
                    'sale_order_id')):  # restore old cart or merge with unexistant
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive == 'merge':
                abandoned_order.order_line.write({'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session.get(
                    'sale_order_id'):  # abandoned cart found, user have to choose what to do
                values.update({'access_token': abandoned_order.access_token})

        values.update({
            'website_sale_order': order,
            'date': fields.Date.today(),
            'suggested_products': [],
            'cart_timeout': post.get('timeout', False)
        })
        if order:
            order.order_line.filtered(lambda l: not l.product_id.active).unlink()
            _order = order
            if not request.env.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        if post.get('type') == 'popover':
            # force no-cache so IE11 doesn't cache this XHR
            return request.render("website_sale.cart_popover", values, headers={'Cache-Control': 'no-cache'})

        return request.render("website_sale.cart", values)


class PaymentPortalInherit(PaymentPortal):

    @http.route()
    def shop_payment_transaction(self, *args, **kwargs):
        """ Payment transaction override to double check cart quantities before
        placing the order
        """
        order = request.website.sale_get_order()
        order.check_registration_availability()
        print("order cannot be delete")
        order.write({'payment_start': True})

        return super().shop_payment_transaction(*args, **kwargs)
