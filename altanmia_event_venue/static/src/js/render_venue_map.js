odoo.define('altanmia_event_venue.render_venue_map', function (require) {
    'use strict';

    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');
    var d3 = window.d3;

    var RenderVenueMap = AbstractField.extend({
        supportedFieldTypes: ['binary'],

        _render: function () {
            if (this.recordData && this.recordData[this.name]) {
                var self = this;
                var mapUrl = '/web/binary/map?model=' + this.model + '&field=' + this.name + '&id=' + this.res_id;

                // Render the binary file widget
                this._renderBinaryFileWidget();

                // Load and render the SVG
                d3.text(mapUrl)
                    .then(function (svgData) {
                        var parser = new DOMParser();
                        var xmlDoc = parser.parseFromString(svgData, 'image/svg+xml');
                        var svgElement = xmlDoc.documentElement;

                        self._attachSectionClickEvent(svgElement);

                        // self.$el.empty();
                        self.$el.append(svgElement);
                    })
                    .catch(function (error) {
                        console.log('Error loading SVG:', error);
                    });
            } else {
                // Render the binary file widget when no data is available
                this._renderBinaryFileWidget();
            }
        },

        _renderBinaryFileWidget: function () {
            // Render the binary file widget using the original _render method
            AbstractField.prototype._render.call(this);
        },

        _attachSectionClickEvent: function (svgElement) {
            var self = this;
            d3.select(svgElement)
                .selectAll('.section')
                .on('click', function (event, d) {
                    console.log('Clicked section:', d.section);
                    self._selectSection(d.id); // Add your logic to handle section selection
                });
        },

        _selectSection: function (sectionId) {
            // Implement your logic to handle section selection
            // This method will be called when a section is clicked
            // You can perform any actions you need based on the selected section
        },
    });

    fieldRegistry.add('render_venue_map', RenderVenueMap);

    return RenderVenueMap;
});
