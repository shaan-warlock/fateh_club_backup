odoo.define('altanmia_event_venue.event_venue_layout', function (require) {

    var ajax = require('web.ajax');
    var core = require('web.core');
    var Widget = require('web.Widget');
    var publicWidget = require('web.public.widget');
    var Dialog = require('web.Dialog');
    var session = require('web.session');

    var _t = core._t;
    var d3 = window.d3;

    publicWidget.registry.EventVenueLayout = publicWidget.Widget.extend({
        selector: '#registration_form',
        events: {
                'click .ticket': 'selectTicket',
                'click .fa-plus': 'increaseInput',
                'click .fa-minus': 'decreaseInput',
                'change .ticket-num': 'numTicketChange',
            },

        start: async function() {
          await this._openPopup();
          const venue_id = this.$('#stadium-map').data('venue');
          this.max_event_limit = this.$('#event_max_limit').data('maxlimitevent');
          const self = this;
          // Add an input event listener to all input elements
            this.$('input[type="number"]').on('input', this.handleInputChange.bind(this));
          if (venue_id === undefined){
            return;
          }

          const res = await this._rpc({
            route: '/event/layout',
            params: {
              venue_id: venue_id,
            },
          }).then(function(data) {
            const stadiumData = data.sections;
            const svg = d3
              .select('#stadium-map')
              .append('svg')
              .style('background-image', `url(${data.sections_background})`)
              .style('background-size', 'contain')
              .style('background-repeat', 'no-repeat')
              .attr('viewBox', `0 0 ${data.width} ${data.high}`);

            self.sections = svg
              .selectAll('.section')
              .data(stadiumData)
              .enter()
              .append('g')
              .attr('class', 'section');

            self.sections
              .append('path')
              .attr('id', d => d.id)
              .attr('class', d => `section-path section-${d.id}`)
              .attr('d', d => d.vector)
              .style('fill', d => d.color);

            self.sections
              .append('text')
              .attr('class', 'section-label')
              .attr('text-anchor', 'middle')
              .attr('dominant-baseline', 'hanging')
              .attr('x', d => {
                // Get the bounding box of the section path
                const sectionPath = document.querySelector(`.section-${d.id}`);
                const sectionBBox = sectionPath.getBBox();
                return sectionBBox.x + sectionBBox.width / 2;
              })
              .attr('y', d => {
                // Get the bounding box of the section path
                const sectionPath = document.querySelector(`.section-${d.id}`);
                const sectionBBox = sectionPath.getBBox();
                return sectionBBox.y+1.5;
              })
              .text(d => d.code);

            self.sections.on('click', (event, d) => {
              self.selectSection([d.id]);

              // Find all tickets elements with the specified data-section value
              $('.ticket').removeClass('highlight');
              const ticketDiv = $('div[data-section]').filter(function() {
                const sectionArray = $(this).data('section');
                return sectionArray.includes(d.id);
              });
              ticketDiv.addClass('highlight');
            });
          });
        },

        _openPopup: function () {
                    var self = this;
                    const event_id = this.$('#event_id').data('event');
                    var hasPopupBeenShown = sessionStorage.getItem(`popup_shown_${event_id}`);
                    if (!hasPopupBeenShown) {
                       // If the popup has not been shown, show it and mark it as shown
                       var $notes;
                       var def = this._rpc({
                           route: '/event/note',
                           params: {
                               event_id: event_id,
                           },
                       }).then(function (note) {
                           $notes = note;
                           var accepted = false;
                           var $htmlObject = document.createElement('div');
                           let popup_dialog_obj = document.querySelector(".o_dialog_container");
                           var language = document.documentElement.lang;
                           if (!popup_dialog_obj){
                                return;
                           }
                           if (language == 'ar-001'){
                                popup_dialog_obj.style.direction = 'rtl'
                                popup_title_name = "الشروط و الأحكام"
                                popup_accept_btn = "موافق"
                                popup_deny_btn = "أرفض"
                                $htmlObject.style.direction = 'rtl';
                                $htmlObject.style.textAlign = 'right';
                           }
                           else
                           {
                                popup_dialog_obj.style.direction = 'ltr'
                                popup_title_name = "Terms and Conditions"
                                popup_accept_btn = "Accept"
                                popup_deny_btn = "Deny"
                                $htmlObject.style.direction = 'ltr';
                                $htmlObject.style.textAlign = 'left';
                           }
                           $htmlObject.innerHTML = $notes;
                           var dialog = new Dialog(this, {
                               title: popup_title_name,
                               size: 'medium',
                               $content: $htmlObject,
                               buttons: [
                                   {
                                       text: popup_accept_btn,
                                       classes: 'btn-secondary',
                                       close: true,
                                       click: function(){
                                           accepted = true;
                                           var is_policy_accepted = this.$('#is_policy_accepted').value;
                                           is_policy_accepted = true;
                                           // Store that the popup has been shown for this event
                                           sessionStorage.setItem(`popup_shown_${event_id}`, 'true');
                                       }
                                   },
                                   {
                                       text: popup_deny_btn,
                                       classes: 'btn-secondary',
                                       close: true,
                                       click: function (ev) {
                                           var self = this;
                                           var url = '/event/';
                                           window.location.href = url;
                                       },
                                   },
                               ],
                           });
                           dialog.on("closed", self, function () {
                               if (!accepted) {
                                   var url = '/event/';
                                   window.location.href = url;
                               }
                           });

                           dialog.open();
                       });

                   }
               },

        denyPolicy : function (ev) {
            var self = this;
            var eventID = $('#eventID').val();
            var eventName = $('#eventName').val();
            var urlEventName = eventName.toLowerCase().replace(/ /g, '-');
//            var url = '/event/' + urlEventName +'-'+ + eventID + '/register';
            var url = '/event/'
            window.location.href = url;
            },

        selectSection: function(sectionIds){
            if(!this.sections){
                return;
            }
            // Reset borders for all sections
            this.sections.selectAll('.section-path').style('stroke', 'none').style('fill', d => d.color);
            // Reset weight for all labels
            this.sections.selectAll('.section-label').style('font-weight', 'normal');
            sectionIds.forEach(sectionId => {
                const section = this.sections.filter(d => d.id === sectionId);
                const sectionColor = section.datum().color;
                const darkerColor = d3.color(sectionColor).darker(0.7);
                const lighterColor = d3.interpolateRgb(sectionColor, 'white')(0.3);

                // Example: Update the stroke and stroke width of the section
                section.select('.section-path')
                      .style('stroke', darkerColor)
                      .style('fill', d => lighterColor)
                      .style('stroke-width', '0.5px');

                // Example: Update the font weight of the section label
                section.select('.section-label')
                      .style('font-weight', '900');
             });

        },

        selectTicket:function(event){
            if (this.$(event.currentTarget).data('section') === undefined){
                return;
            }
            const sectionArrayStr = this.$(event.currentTarget).data('section').toString();
            var sectionIds = sectionArrayStr.split(",").map(Number);

            this.selectSection(sectionIds);

            // Find all tickets elements with the specified data-section value
            $('.ticket').removeClass('highlight');
            this.$(event.currentTarget).addClass('highlight');
        },

        numTicketChange: function(event){
            debugger
            this.validateInput(this.$(event.currentTarget))
        },

        validateInput: function(input) {
            const self = this;  // Preserve the 'this' context
            const maxLimit = input.data('max');
            const ticketId = input.data('id');
            const availableNum = input.data('available');
            const $button = this.$('.register-btn');
            const tv = parseInt(input.val(), 10) || 0;  // Ensure valid number
            const error = this.$('.error');
            const total_error = this.$('.error-total');

            // Reset input if invalid
            if (isNaN(tv) || tv < 0) {
                input.val(0);
            }

            // Calculate total reserved tickets
            let reserved_ticket = 0;
            this.$('.ticket-num').each(function () {
                reserved_ticket += parseInt($(this).val() || 0);
            });

            // RPC call to validate ticket quantity
            this._rpc({
                route: '/event/check/ticket_quantity',
                params: {
                    'ticket_id': ticketId,
                    'max_reserve': maxLimit,
                    'available': availableNum,
                    'tv': tv,
                    'max_event_limit': this.max_event_limit
                }
            }).then(function(data) {
                const maxlimitevent = self.$('#event_max_limit').data('maxlimitevent');

                // Check total reserved tickets for the event
                if (reserved_ticket > maxlimitevent) {
                    total_error.addClass("register-invalid");
                    total_error.html(_t(`You cannot reserve tickets for this event more than (${maxlimitevent})`));
                    total_error.removeClass("d-none");
                } else {
                    total_error.removeClass("register-invalid");
                    total_error.addClass("d-none");
                }

                // Check individual ticket validation
                if (!data.success) {
                    input.addClass("register-invalid");
                    self.$(`#error-${ticketId}`).html(_t(data.message));
                    self.$(`#error-${ticketId}`).removeClass("d-none");
                } else {
                    input.removeClass("register-invalid");
                    self.$(`#error-${ticketId}`).addClass("d-none");
                }

                // Update register button state
                if ($('.register-invalid').length > 0) {
                    $button.attr('disabled', true);
                    $button.addClass("btn-danger");
                    $button.removeClass("btn-primary");
                } else {
                    $button.removeClass("btn-danger");
                    $button.addClass("btn-primary");
                    $button.attr('disabled', false);
                }
            });
        },

        increaseInput: function (event) {
            const inputElement = $(event.currentTarget).siblings('input[type="number"]');

            // Remove the input event listener temporarily
            inputElement.off('input');

            let currentValue = parseInt(inputElement.val(), 10);
            if (!isNaN(currentValue)) {
                currentValue += 1;
                inputElement.val(currentValue);

                // Update the corresponding select option value
                const selectElement = inputElement.siblings('select');
                selectElement.val(currentValue);
            }
            debugger
            this.validateInput(inputElement);
            // Re-add the input event listener
            inputElement.on('input', this.handleInputChange.bind(this));
        },
        decreaseInput: function (event) {
            const inputElement = $(event.currentTarget).siblings('input[type="number"]');

            // Remove the input event listener temporarily
            inputElement.off('input');
            let currentValue = parseInt(inputElement.val(), 10);
            if (!isNaN(currentValue) && currentValue > 0) {
                currentValue -= 1;
                inputElement.val(currentValue);

                // Update the corresponding select option value
                const selectElement = inputElement.siblings('select');
                selectElement.val(currentValue);
            }
            this.validateInput(inputElement);
            // Re-add the input event listener
            inputElement.on('input', this.handleInputChange.bind(this));
        },
        handleInputChange: function(event) {
            const inputElement = $(event.currentTarget);
            const currentValue = parseInt(inputElement.val(), 10);
            if (!isNaN(currentValue)) {
                // Update the corresponding select option value
                const selectElement = inputElement.siblings('select');
                selectElement.val(currentValue);
            }
        },
    });
});

