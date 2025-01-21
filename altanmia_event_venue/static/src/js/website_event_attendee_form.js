odoo.define('website_event.website_event_inherit', function (require) {

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var publicWidget = require('web.public.widget');

var _t = core._t;

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = Widget.extend({

    /**
     * @override
     */
    start: function () {
        var self = this;
        var res = this._super.apply(this.arguments).then(function () {
            $('#registration_form .a-submit')
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
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form');
        var $button = $(ev.currentTarget).closest('[type="submit"]');
        var post = {};
        $('#registration_form table').siblings('.alert').remove();
        $('#registration_form select').each(function () {
            post[$(this).attr('name')] = $(this).val();
        });
        var tickets_ordered = _.some(_.map(post, function (value, key) { return parseInt(value); }));
        if (!tickets_ordered) {
            $('<div class="alert alert-info"/>')
                .text(_t('Please select at least one ticket.'))
                .insertAfter('#registration_form table');
            return new Promise(function () {});
        } else {
            $button.attr('disabled', true);
            return ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
                var $modal = $(modal);
                $modal.modal({backdrop: 'static', keyboard: false});
                $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
                $modal.appendTo('body').modal();
                $modal.on('click', '.js_goto_event', function () {
                    console.log('hiiiiiiiii');
                    $modal.modal('hide');
                    $button.prop('disabled', false);
                });
                $modal.on('click', '.js_continue_event', function () {
                    console.log('grooouups');
                    let summed = 0
                    let groups = document.querySelectorAll('.tickets_form');

                    groups.forEach((group) => {
                        let qtys = group.querySelectorAll('.input_quantity');
                        qtys.forEach((qty) => {
                            summed += parseInt(qty.value)
                            console.log('group' , qty.value, summed, document.getElementById('total_quantity').value)
                        });
                        if(summed>document.getElementById('total_quantity').value){
                         console.log('done by omar ',typeof(group))

                         group.querySelector('.msg').value = 'Cannot distribute tickets with more that you ordered ! '
                         group.querySelector('.msg').style.display = 'block'
                         group.querySelector('.hiddeninput').value= ''
                        }
                        else
                        {
                        group.querySelector('.hiddeninput').value= ' added'
                        group.querySelector('.msg').style.display = 'none'

                        }
                        summed=0
                    });
//                    var total__quantity = $(this).attr("total_quantity");
//                    console.log('total quant is ',total__quantity);

//                    if (yourCondition) {
//                        // Disable the button
//                        $('.js_continue_event').prop('disabled', true);
//                    }
                });
                // my part of the code that does the duplication.
                $modal.on('click', '.addButton1', function(e) {

                console.log('I got here newwwwwwwwwwwwwww ');
                console.log(e.currentTarget);
                const container = e.currentTarget.parentNode.parentNode.previousElementSibling;
                console.log(container);
                let clonedDiv = container.cloneNode(true);

                let inputFields = clonedDiv.querySelectorAll('.form-control');
                inputFields.forEach((input) => {
                  input.value = '' || null;
                });
                container.parentNode.insertBefore(clonedDiv, container.nextSibling);
                let addButton = e.currentTarget
                if (addButton.parentNode.querySelector('.xButton') === null){
                    console.log('remove is here 11111111111');
                    console.log(addButton);
                    $(_t('<span>     </span><a class="btn btn-danger ms-2 me-2 xButton">  -  </a>')).insertAfter(addButton);
                }

                clonedDiv = $(clonedDiv);
                console.log("type of ", typeof(clonedDiv))

//                var counter = parseInt($("#sectionCounter").val()) + 1;
//                var counter = parseInt($("#counter_1").val());
                var counter = parseInt(clonedDiv.find('#counter_1').val());
                // Update input names in the cloned section
                clonedDiv.find("input").each(function () {
                  var oldName = $(this).attr("name");
                  console.log('names');
                  console.log('--------------------------------- counter --------------------------------------');
                  console.log(counter);
                  console.log($("#counter_1").val());
                  console.log(oldName);
                  digit1 = oldName.split('-')[0];
                  digit2 = oldName.split('-')[1];
                  var counter2 = parseInt(digit2) + 1;
//                  console.log(digit);
                  console.log('newName 1');
                  console.log('values ');
                  console.log(digit1);
                  console.log(digit2);
//                  if(digit1 == 1 && digit2 == 0){
//                    counter = 1;
//                  }
//                  oldName[0]=counter;
//                  console.log(newName);
//                  oldName[2]=counter2;
                  const newName = counter + oldName.substring(1, 2) + counter2 + oldName.substring(3);
                  console.log('naaaaaaaaaaaaaaaaaaaaaaaaaaaame',newName);
                  $(this).attr("name", newName);
                });

                },);

                $modal.on('click', '.xButton', function(e){
                    const container = e.currentTarget.parentNode.parentNode.previousElementSibling;
                    console.log('previous siblings');
                    console.log(container.previousElementSibling.previousElementSibling);
                    if(container.previousElementSibling.previousElementSibling != null){
                        container.remove();
                    }
                });
                $modal.on('click', '.close', function () {
                    $button.prop('disabled', false);
                });
            });
        }
    },
});

publicWidget.registry.EventRegistrationFormInstance = publicWidget.Widget.extend({
    selector: '#registration_form',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.instance = new EventRegistrationForm(this);
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

return EventRegistrationForm;
});
