odoo.define('altanmia_event_venue.website_event', function (require) {

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var publicWidget = require('web.public.widget');

var _t = core._t;

// Catch registration form event, because of JS for attendee details
var SeasonTicketForm = Widget.extend({
    /**
     * @override
     */
    start: function () {
    console.log('sdadasd 2142432')
        var self = this;_ticket
        $("#buy_btn").prop('disabled', false);
        var res = this._super.apply(this.arguments).then(function () {
          console.log('sdadasd 2142432')
            $('#season_ticket_form .a-submit')
                .off('click')
                .click(function (ev) {
                    self.on_click(ev);
                });
        });
        return res;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    on_click: function (ev) {
    console.log('doooooo')
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form');
        var $button = $(ev.currentTarget).closest('[type="submit"]');
        var post = {};
        $('#season_ticket_form input').each(function () {
            post[$(this).attr('name')] = $(this).val();
        });
        $button.attr('disabled', true);
        return ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $(modal);
                $modal.modal({backdrop: 'static', keyboard: false});
                $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
                $modal.appendTo('body').modal();
                $modal.on('click', '.js_goto_event', function () {
                console.log('asd b6e5')
                    $modal.modal('hide');
                    $button.prop('disabled', false);
                });
                $modal.on('click', '.close', function () {
                    $button.prop('disabled', false);
                });
            });
    },
});

publicWidget.registry.SeasonTicketFormInstance = publicWidget.Widget.extend({
    selector: '#season_ticket_form',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.instance = new SeasonTicketForm(this);
        return Promise.all([def, this.instance.attachTo(this.$el)]);
    },
    /**
     * @override
     */
    destroy: function () {
        this.instance.setElement(null);
        this._super.apply(this, arguments);
        this.instance.setElement(this.$el);
    },
});

return SeasonTicketForm;
});
