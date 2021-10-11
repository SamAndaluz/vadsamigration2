# -*- coding: utf-8 -*-
{
    'name': "ITL Stock Picking",

    'summary': """
        Este módulo añade a la compañía dentro de la validación para la salida de almacén evitando el error: A serial number should only be linked to a single product.""",

    'description': """
        Este módulo añade a la compañía dentro de la validación para la salida de almacén evitando el error: A serial number should only be linked to a single product.
    """,

    'author': "ITLigthen",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}