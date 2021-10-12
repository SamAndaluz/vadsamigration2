# -*- coding: utf-8 -*-
{
    'name': "ITL Sale Operating Unit",

    'summary': """
        Este módulo agrega un nuevo campo en la configuración del usuario para tener dos unidades operativas.""",

    'description': """
        Este módulo agrega un nuevo campo en la configuración del usuario para tener dos unidades operativas.
    """,

    'author': "ITLighten",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '14.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_operating_unit'],

    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'views/res_users_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}