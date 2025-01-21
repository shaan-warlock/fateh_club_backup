from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

_INTERVALS = {
    'minutes': lambda interval: relativedelta(minutes=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'now': lambda interval: relativedelta(hours=0),
}

class EventTypeMail(models.Model):
    _inherit = 'event.type.mail'

    interval_type = fields.Selection(selection_add=[
        ('after_paid_confirm', 'After paid ticket confirm'),
        ('after_gift_confirm', 'After gift ticket confirm'),
    ], ondelete={'after_paid_confirm': 'set default', 'after_gift_confirm': 'set default'})


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    interval_type = fields.Selection(selection_add=[
        ('after_paid_confirm', 'After paid ticket confirm'),
        ('after_gift_confirm', 'After gift ticket confirm'),
    ], ondelete={'after_paid_confirm': 'set default', 'after_gift_confirm': 'set default'})

    interval_unit = fields.Selection(selection_add=[
        ('minutes', 'Minutes')],
        ondelete={'minutes': 'set default'})

    @api.depends('event_id.date_begin', 'event_id.date_end', 'interval_type', 'interval_unit', 'interval_nbr')
    def _compute_scheduled_date(self):
        for scheduler in self:
            if scheduler.interval_type in ['after_sub', 'after_paid_confirm', 'after_gift_confirm']:
                date, sign = scheduler.event_id.create_date, 1
            elif scheduler.interval_type == 'before_event':
                date, sign = scheduler.event_id.date_begin, -1
            else:
                date, sign = scheduler.event_id.date_end, 1

            scheduler.scheduled_date = date + _INTERVALS[scheduler.interval_unit](sign * scheduler.interval_nbr) if date else False



    @api.depends('interval_type', 'scheduled_date', 'mail_done')
    def _compute_mail_state(self):
        for scheduler in self:
            # registrations based
            if scheduler.interval_type in ['after_sub', 'after_paid_confirm', 'after_gift_confirm']:
                scheduler.mail_state = 'running'
            # global event based
            elif scheduler.mail_done:
                scheduler.mail_state = 'sent'
            elif scheduler.scheduled_date:
                scheduler.mail_state = 'scheduled'
            else:
                scheduler.mail_state = 'running'

    def execute(self):
        for scheduler in self:
            now = fields.Datetime.now()
            if scheduler.interval_type in ['after_sub', 'after_paid_confirm', 'after_gift_confirm']:
                domain = [('state', 'not in', ('cancel', 'draft'))]
                if scheduler.interval_type == 'after_paid_confirm':
                    domain = domain + [('payment_status', '!=', 'free')]
                elif scheduler.interval_type == 'after_gift_confirm':
                    domain = domain + [('payment_status', '=', 'free')]
                new_registrations = scheduler.event_id.registration_ids.filtered_domain(domain) - scheduler.mail_registration_ids.registration_id
                scheduler._create_missing_mail_registrations(new_registrations)

                # execute scheduler on registrations
                scheduler.mail_registration_ids.execute()
                total_sent = len(scheduler.mail_registration_ids.filtered(lambda reg: reg.mail_sent))
                scheduler.update({
                    'mail_done': total_sent >= (scheduler.event_id.seats_reserved + scheduler.event_id.seats_used),
                    'mail_count_done': total_sent,
                })
            else:
                # before or after event -> one shot email
                if scheduler.mail_done or scheduler.notification_type != 'mail':
                    continue
                # no template -> ill configured, skip and avoid crash
                if not scheduler.template_ref:
                    continue
                # do not send emails if the mailing was scheduled before the event but the event is over
                if scheduler.scheduled_date <= now and (scheduler.interval_type != 'before_event' or scheduler.event_id.date_end > now):
                    scheduler.event_id.mail_attendees(scheduler.template_ref.id)
                    scheduler.update({
                        'mail_done': True,
                        'mail_count_done': scheduler.event_id.seats_reserved + scheduler.event_id.seats_used,
                    })
        return True


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    @api.depends('registration_id', 'scheduler_id.interval_unit', 'scheduler_id.interval_type')
    def _compute_scheduled_date(self):
        for mail in self:
            if mail.registration_id:
                date_open = mail.registration_id.date_open
                date_open_datetime = date_open or fields.Datetime.now()
                mail.scheduled_date = date_open_datetime + _INTERVALS[mail.scheduler_id.interval_unit](
                    mail.scheduler_id.interval_nbr)
            else:
                mail.scheduled_date = False