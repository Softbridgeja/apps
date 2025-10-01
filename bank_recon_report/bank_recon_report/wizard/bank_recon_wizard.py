# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.misc import format_date


class BankReconWizard(models.TransientModel):
    _name = 'bank.recon.wizard'
    _description = 'Bank Reconciliation Report Wizard'

    date_from = fields.Date(string='Period start', required=True)
    date_to = fields.Date(string='Period end', required=True)
    show_details = fields.Boolean(string='Show detail lines', default=True)
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank journal',
        domain=[('type', '=', 'bank')],
        required=True,
    )
    bank_balance = fields.Monetary(
        string='Bank statement balance',
        currency_field='company_currency_id',
        required=True,
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        default=lambda s: s.env.company.currency_id,
    )

    report_data = fields.Json(compute='_compute_report_data')

    # ------------------------------------------------------------------
    #  helpers
    # ------------------------------------------------------------------
    def _get_opening_balance(self):
        self.ensure_one()
        date_before = fields.Date.subtract(self.date_from, days=1)
        self.env.cr.execute("""
            SELECT COALESCE(SUM(aml.balance), 0)
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.journal_id = %s
              AND aml.date <= %s
              AND am.state = 'posted'
        """, (self.journal_id.id, date_before))
        return self.env.cr.fetchone()[0]

    def _get_period_moves(self):
        """Return dict with keys: debit, credit, unp_chks, unp_lodgs"""
        self.ensure_one()

        # 1. total debits / credits
        self.env.cr.execute("""
            SELECT
                COALESCE(SUM(aml.debit), 0) AS debit,
                COALESCE(SUM(aml.credit), 0) AS credit
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.journal_id = %s
              AND aml.date BETWEEN %s AND %s
              AND am.state = 'posted'
        """, (self.journal_id.id, self.date_from, self.date_to))
        debit, credit = self.env.cr.fetchone()

        # 2. unpresented checks  (outgoing payments NOT on any statement)
        self.env.cr.execute("""
            SELECT COALESCE(SUM(aml.balance), 0)
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.journal_id = %s
              AND aml.date BETWEEN %s AND %s
              AND am.state = 'posted'
              AND aml.payment_id IS NOT NULL
              AND aml.credit > 0
              AND aml.statement_line_id IS NULL
        """, (self.journal_id.id, self.date_from, self.date_to))
        unp_chks = abs(self.env.cr.fetchone()[0] or 0)

        # 3. unpresented lodgements (incoming payments NOT on any statement)
        self.env.cr.execute("""
            SELECT COALESCE(SUM(aml.balance), 0)
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.journal_id = %s
              AND aml.date BETWEEN %s AND %s
              AND am.state = 'posted'
              AND aml.payment_id IS NOT NULL
              AND aml.debit > 0
              AND aml.statement_line_id IS NULL
        """, (self.journal_id.id, self.date_from, self.date_to))
        unp_lodgs = self.env.cr.fetchone()[0] or 0

        return {
            'debit': debit,
            'credit': credit,
            'unpresented_checks': unp_chks,
            'unpresented_lodgements': unp_lodgs,
        }

    @api.depends('date_from', 'date_to', 'journal_id', 'bank_balance')
    def _compute_report_data(self):
        for wiz in self:
            opening = wiz._get_opening_balance()
            period  = wiz._get_period_moves()
            closing = opening + period['debit'] - period['credit']
            wiz.report_data = {
                'journal' : wiz.journal_id.name,
                'date_from': format_date(wiz.env, wiz.date_from),
                'date_to'  : format_date(wiz.env, wiz.date_to),
                'opening'  : opening,
                'debit'    : period['debit'],
                'credit'   : period['credit'],
                'unp_chks' : period['unpresented_checks'],
                'unp_lodgs': period['unpresented_lodgements'],
                'closing'  : closing,
                'bank_bal' : wiz.bank_balance,
                'variance' : closing - wiz.bank_balance,
                'show_details': wiz.show_details, 
            }

    def _get_unreconciled_lines(self):
        """Return list of dicts for lines without statement_line_id"""
        self.ensure_one()
        self.env.cr.execute("""
            SELECT aml.date,
                   aml.name       AS ref,
                   rp.name        AS partner,
                   aml.debit,
                   aml.credit,
                   abs(aml.balance) AS amount
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            LEFT JOIN res_partner rp ON rp.id = aml.partner_id
            WHERE aml.journal_id = %s
              AND aml.date BETWEEN %s AND %s
              AND am.state = 'posted'
              AND aml.payment_id IS NOT NULL
              AND aml.statement_line_id IS NULL
            ORDER BY aml.date, aml.id
        """, (self.journal_id.id, self.date_from, self.date_to))
        return self.env.cr.dictfetchall()

    # ------------------------------------------------------------------
    #  buttons  –  used by the form view
    # ------------------------------------------------------------------
    def preview_on_screen(self):
        """Open PDF in same window (no download)"""
        return self.print_report()

    def print_report(self):
        """Download PDF"""
        return self.env.ref('bank_recon_report.action_bank_recon_report').report_action(self)