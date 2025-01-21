odoo.define('new.ticket_details', function (require) {
    var publicWidget = require('web.public.widget');

    publicWidget.registry.eventticketdeatalis = publicWidget.Widget.extend({
        selector: '.o_wevent_js_ticket_details',

        start: function (){
            this.$('.o_wevent_registration_btn').click();
            return this._super.apply(this, arguments);
        },
    });

return publicWidget.registry.eventticketdeatalis;
});
