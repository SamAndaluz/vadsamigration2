# -*- coding: utf-8 -*-
{
    'name': "Descarga masiva de facturas",

    'summary': """
        Este módulo permite la descarga masiva y automática de facturas con Prodigia.""",

    'description': """
        Este módulo permite la descarga masiva y automática de facturas con Prodigia.
    """,

    'author': "ITLighten",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','account','stock','l10n_mx_edi'],

    # always loaded
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/requests.xml',
        'views/settings.xml',
        'views/templates.xml',
        'views/company.xml',
        'data/cron_jobs.xml',
        'wizard/sh_message_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True
}
