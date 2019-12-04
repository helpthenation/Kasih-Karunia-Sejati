{
    'name':"Product Expiry Notification",
    'summary': """Product expiry through email""",
    'description': 'Product Booking',
    'author': "HashMicro / Niyas",
    'website':"http://www.hashmicro.com",
    'depends': [ 'product_expiry'],
    'data': [
        'data/expiry_email_template.xml',
        'views/stock_production_lot_view.xml'

    ],
    'category': 'booking',
    'version':'1.0',
    'application': True,
}
