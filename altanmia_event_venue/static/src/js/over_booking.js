odoo.define('altanmia_event_venue.OverBooking', function (require) {
    'use strict';

    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    publicWidget.registry.PaymentPostProcessing.include({
        xmlDependencies: publicWidget.registry.PaymentPostProcessing.prototype.xmlDependencies.concat(
            ['/altanmia_event_venue/static/src/xml/over_booking.xml']
        ),
        // Override the poll function
        poll: function () {
            var self = this;
            this._rpc({
                route: '/payment/status/poll',
                params: {
                    'csrf_token': core.csrf_token,
                }
            }).then(function(data) {
                if(data.success === true) {
                    self.processPolledData(data.display_values_list);
                }
                else {
                    switch(data.error) {
                    case "tx_process_retry":
                        break;
                    case "tx_ticket_overbook":
                        self.displayContent("altanmia_event_venue.ticket_overbook", {});
                        break;
                    case "no_tx_found":
                        self.displayContent("payment.no_tx_found", {});
                        break;
                    default: // if an exception is raised
                        self.displayContent("payment.exception", {exception_msg: data.error});
                        break;
                    }
                }
                self.startPolling();

            }).guardedCatch(function() {
                self.displayContent("payment.rpc_error", {});
                self.startPolling();
            });
        },
    });

});
