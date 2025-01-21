odoo.define('altanmia_event_venue.website_cart_timer', function (require) {
    var core = require('web.core');
    var Widget = require('web.Widget');
    var publicWidget = require('web.public.widget');
    var _t = core._t;
    var d3 = window.d3;


    publicWidget.registry.WebsiteCartTimer = publicWidget.Widget.extend({
        selector: '.o_wsale_my_cart',
        timerInterval: null,
        remainingTime: 0,

        start: async function() {
            var remainingTimeText = this.$('.my_cart_timer').text();
            var remainingTimeArray = remainingTimeText.split(':');
            this.remainingTime = parseInt(remainingTimeArray[0]) * 60 + parseInt(remainingTimeArray[1]);

            // this.updateTimer();

            if(this.$('.my_cart_timer').length !==0 ){
                this.timerInterval = setInterval(this.updateTimer.bind(this), 1000); // Update every second
            }
        },

         destroy: function () {
            clearInterval(this.timerInterval); // Clear the interval when the widget is destroyed
            this._super.apply(this, arguments);
        },

        updateTimer: function () {
            const qty = parseInt(this.$('.my_cart_quantity').text());
            if (qty<=0){
                return
            }
            var minutes = Math.floor(this.remainingTime / 60);
            var seconds = this.remainingTime % 60;
            var formattedTime = minutes.toString().padStart(2, '0') + ':' + seconds.toString().padStart(2, '0');
            this.$('.my_cart_timer').text(formattedTime);

            if (this.remainingTime > 0) {
                this.remainingTime -= 1;
            } else {
                 this._rpc({
                    route: '/sale/cart/clear',
                  }).then(function(data) {
                    if(data){
                        window.location = '/shop/cart?timeout=1';
                    }
                  });

                clearInterval(this.timerInterval); // Stop the timer when it reaches zero

            }
        },

    });


});