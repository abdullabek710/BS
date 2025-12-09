# -*- coding: utf-8 -*-
{
    'name': "Client Cashback Management System",

    'summary': "Specific type of client cashback system",

    'description': """
Long description of module's purpose
    """,

    'author': "Abdullabek",
    'website': "https://www.yourcompany.com",

    'category': 'Customization',
    'version': '0.1',

    'depends': ['base',
                'contacts',
                'account',
                'sale_management',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/res_partner.xml',
        'views/res_config_settings.xml',
        'views/sale_order.xml',

        # crons
        'data/cashback_scheduled_actions.xml',
    ],
    'application': True,
    'installable': True,
    'license':'LGPL-3'
}

