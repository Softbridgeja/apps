{
    'name': 'Bank Reconciliation Report',
    'version': '17.0.2.0.0',
    'category': 'Accounting',
    'summary': 'GL opening / closing + variance vs. bank balance',
    'author': 'Your name',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bank_recon_wizard_view.xml',
        'report/bank_recon_report_template.xml',
    ],
    'installable': True,
    'application': False,
}