import logging
from datetime import timedelta

import psycopg2

from odoo import fields, http, _
from odoo.http import request
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing

_logger = logging.getLogger(__name__)


class PaymentPostProcessingInherit(PaymentPostProcessing):

    @http.route()
    def poll_status(self):
        limit_date = fields.Datetime.now() - timedelta(days=1)
        monitored_txs = request.env['payment.transaction'].sudo().search([
            ('id', 'in', self.get_monitored_transaction_ids()),
            ('last_state_change', '>=', limit_date)
        ])

        if not monitored_txs:  # The transaction was not correctly created
            return {
                'success': False,
                'error': 'no_tx_found',
            }

        # Build the list of display values with the display message and post-processing values
        display_values_list = []
        for tx in monitored_txs:
            display_message = None
            if tx.state == 'pending':
                display_message = tx.acquirer_id.pending_msg
            elif tx.state == 'done':
                display_message = tx.acquirer_id.done_msg
            elif tx.state == 'cancel':
                display_message = tx.acquirer_id.cancel_msg
            display_values_list.append({
                'display_message': display_message,
                **tx._get_post_processing_values(),
            })

        # Stop monitoring already post-processed transactions
        post_processed_txs = monitored_txs.filtered('is_post_processed')
        self.remove_transactions(post_processed_txs)

        # Finalize post-processing of transactions before displaying them to the user
        txs_to_post_process = (monitored_txs - post_processed_txs).filtered(
            lambda t: t.state == 'done'
        )
        success, error = True, None
        try:
            txs_to_post_process._finalize_post_processing()
        except psycopg2.OperationalError:  # A collision of accounting sequences occurred
            request.env.cr.rollback()  # Rollback and try later
            success = False
            error = 'tx_process_retry'
        except Exception as e:
            request.env.cr.rollback()
            success = False
            error = str(e)
            _logger.exception(
                "encountered an error while post-processing transactions with ids %s:\n%s",
                ', '.join([str(tx_id) for tx_id in txs_to_post_process.ids]), e
            )
        if not success:
            for trnsx in monitored_txs:
                orders = trnsx.sale_order_ids.filtered(lambda so: so.has_event_ticket)
                try:
                    orders.check_registration_availability()
                except:
                    return {
                        'success': success,
                        'error': 'tx_ticket_overbook',
                    }

        return {
            'success': success,
            'error': error,
            'display_values_list': display_values_list,
        }
