odoo.define('altanmia_event_venue.modal_actions', function (require) {
    "use strict";

    var publicWidget = require('web.public.widget');

    publicWidget.registry.TransferModal = publicWidget.Widget.extend({
        selector: '#transferModal',
        events: {
            'click #confirmTransfer': '_onConfirmTransfer',
        },

        _onConfirmTransfer: function () {
            var email = $('input')[2].value
            this._rpc({
                route: '/my/ticket/transfer',
                params: {email: email },
            })
            if (!email){
                $('.emailerror').removeClass('d-none')
            }
            if (email){
                $('#transferModal').modal('hide');
            }
        },
    });
});



