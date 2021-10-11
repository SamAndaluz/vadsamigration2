# -*- coding: utf-8 -*-
{
    'name': "ITL CMP Interface",

    'summary': """
        Este módulo agrega la funcionalidad para la conexión con CMP y la lógica para leer los archivos 
        de los directorios de CMP.""",

    'description': """
        Este módulo agrega la funcionalidad para la conexión con CMP y la lógica para leer los archivos 
        de los directorios de CMP.
    """,

    'author': "ITLighten",
    'website': "https://www.itlighten.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security_groups.xml',
        'views/settings_views.xml',
        'views/cmp_views.xml',
        'wizard/cmp_get_file.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}