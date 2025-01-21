odoo.define('altanmia_event_venue.collapse_tickets', function (require) {
    $(document).ready(function () {
        $('.toggle-group-collapse').on('click', function (e) {
            e.preventDefault();
            var group = $(this).data('group');
            var sanitizedGroup = group.replace(/ /g, '_');
            var ticketGroupId = 'group-' + sanitizedGroup;
            var ticketGroup = $('#' + ticketGroupId);
            if (ticketGroup.length > 0) {
                ticketGroup.toggle();
                if (ticketGroup.is(':visible')) {
                    $(this).text(' Hide');
                } else {
                    $(this).text(' Show');
                }
            } else {
                console.error('Element not found for ID:', ticketGroupId);
            }
        });
    });
});