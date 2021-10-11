# -*- coding: utf-8 -*-
{
    'name': "ITL 99 Minutos",

    'summary': """
        This module adds functionality to create shipping order from 99 minutos.""",

    'description': """
        This module adds functionality to create shipping order from 99 minutos.
    """,

    'author': "Itlighten",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account', 'delivery', 'mail', 'stock','stock_account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/settings.xml',
        #'views/templates.xml',
        'data/delivery_99minutos_data.xml',
        'views/delivery_99minutos_views.xml',
        'views/stock_picking.xml',
        'views/notification_views.xml',
        'views/partner_views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}