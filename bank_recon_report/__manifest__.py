{
    'name': 'Bank Reconciliation Report',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'GL opening / closing + variance vs. bank balance (Excel/PDF)',
    'author': 'Soft Bridge Solutions Ltd',
    'depends': ['account', 'base'],
    'data': ['security/ir.model.access.csv', 'wizard/bank_recon_wizard_view.xml', 'report/bank_recon_report_template.xml', 'wizard/bank_recon_actions.xml'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3'
}
