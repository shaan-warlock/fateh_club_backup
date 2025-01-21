odoo.define('altanmia_event_venue.refresh_qr_page', function (require) {
    var publicWidget = require('web.public.widget');

    publicWidget.registry.refreshQrcodePage = publicWidget.Widget.extend({
        selector: '.js_refresh_qr_page',

        start: function (){
        	setInterval(function() {
		        window.location.reload()
		    }, 60000);
        }
    })
});
