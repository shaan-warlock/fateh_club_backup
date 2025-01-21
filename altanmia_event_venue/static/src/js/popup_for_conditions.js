//odoo.define('altanmia_event_venue.popup', function (require) {
//    "use strict";
//
//    var core = require('web.core');
//    var Dialog = require('web.Dialog');
//
//    var _t = core._t;
//
//    $(document).ready(function () {
//        console.log('trdasdasdar')
//        // Handle the click event on the popup trigger
//        $(document).on('click', '.popup-trigger', function () {
//            var options = {
//                title: _t("Popup Title"),
//                $content: $(core.qweb.render('altanmia_event_venue.popup_template')),
//                size: 'medium',
//                buttons: [
//                    {text: _t("Close"), close: true}
//                ],
//            };
//            var dialog = new Dialog(this, options);
//            dialog.open();
//        });
//    });
//
//});
odoo.define('altanmia_event_venue.popup', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var ajax = require('web.ajax');

    var _t = core._t;

    publicWidget.registry.Popup = publicWidget.Widget.extend({
        selector: '#pop-content',

        start: function () {
            console.log("popup");
            this._displayPopup();
        },

        _displayPopup: function () {
            // Use AJAX or other methods to load and display the popup content
            ajax.jsonRpc('/event/<model("event.event"):event>/page/<path:page>', 'call', {}).then(function (modal) {
                var $modal = $(modal);
                $modal.modal({backdrop: 'static', keyboard: false});
                $modal.appendTo('body').modal();
            });
        },
    });

    return {
        Popup: publicWidget.registry.Popup,
    };
});

