odoo.define('altanmia_event_venue.tickets_reservation', function (require) {
    'use strict';
    var core = require('web.core');
    const dom = require('web.dom');
    var _t = core._t;

    var Dialog = require('web.Dialog');
    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    var qweb = core.qweb;
    var rpc = require('web.rpc');

    publicWidget.registry.tickets_reservation = publicWidget.Widget.extend({
            selector: '#attendee_registration',
//            template : 'registration_attendee_details_1',
            events: {
                'click .addButton1': '_copyDiv',
            },
            init : function(){
                console.log('trr')
                this._super.apply(this,arguments)
            },

            start:  function() {
            console.log('lololololoo');
            },

            _copyDiv: function(e) {
                console.log('I got here');
                const container = e.currentTarget.parentNode;
                const parentContainer = container.parentNode;
                console.log(parentContainer);
                let clonedDiv = parentContainer.cloneNode(true);
                let inputFields = clonedDiv.querySelectorAll('.form-control');
                inputFields.forEach((input) => {
                  input.value = '' || null;
                });
                parentContainer.parentNode.insertBefore(clonedDiv, parentContainer.nextSibling);
                let addButton = clonedDiv.querySelector('.addButton')
                if (clonedDiv.querySelector('.xButton') === null){
                    $(_t('<a class="btn btn-danger ms-2 me-2 xButton">حذف</a>')).insertAfter(addButton);
                }
            },
        })
});

//publicWidget.registry.TicketsReservation();