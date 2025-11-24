{
    'name': "Custom Sales Credit Error",

    'summary': "When Credit Limit error exced, quotation cannot be confirmed",

    'description': """
Long description of module's purpose
    """,

    'author': "Abdullabek",
    'website': "https://www.yourcompany.com",
    'category': 'Custom',
    'version': '0.1',
    'depends': ['base', 'sale_management'],
    'post_init_hook':'enable_credit_limit',
    'data': [],
    'application': True,
    'license': 'LGPL-3',

}

