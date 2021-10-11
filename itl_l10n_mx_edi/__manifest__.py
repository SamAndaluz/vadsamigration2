# -*- coding: utf-8 -*-
{
    'name': "ITL Localización Méxicana",

    'summary': """
        Este módulo usa los dígitos decimales de la moneda para calcular los impuestos al timbrar una factura. 
        Además, cambia el template del CFDI 3.3 para agregarle 6 dígitos de precisión a los impuestos.""",

    'description': """
        Este módulo usa los dígitos decimales de la moneda para calcular los impuestos al timbrar una factura. 
        Además, cambia el template del CFDI 3.3 para agregarle 6 dígitos de precisión a los impuestos.
    """,

    'author': "ITlighten",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','l10n_mx_edi'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_currency_views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}