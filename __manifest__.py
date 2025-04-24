{
    'name': 'Códigos de barras compartidos',
    'version': '1.0',
    'summary': 'Permite usar el mismo código de barras para diferentes variantes de producto',
    'description': """
        Este módulo modifica el comportamiento estándar de Odoo para permitir
        que múltiples variantes de un mismo producto compartan el mismo código de barras.
    """,
    'category': 'Inventory',
    'author': 'Asteroid',
    'website': 'https://asteroid.cx',
    'license': 'LGPL-3',
    'depends': ['product', 'stock', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'shared_barcode/static/src/js/shared_barcode.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}