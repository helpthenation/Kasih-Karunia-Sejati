# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError

    
class IrSequence(models.Model):
    _inherit = "ir.sequence"
    
    reset_sequence = fields.Selection([('daily', 'Daily'), ('monthy', 'Monthy'), ('yearly', 'Yearly')],
                                      string='Reset Sequence', required=True, default='daily',)
    number_next_actual = fields.Integer(string='Next Number',
                                        help="Next number that will be used. This number can be incremented "
                                        "frequently so the displayed value might already be obsolete")
                                        
    reset = fields.Selection([('enable', 'Enable'), ('disable', 'Disable')],
                                      string='Reset', required=True, default='disable',)                                  
    def reset_sequnce(self):
        sequences = self.env['ir.sequence'].search([('implementation','=','standard')])
        date = datetime.now()
        for sequence in sequences:
            #if sequence.use_date_range == True:
            #    sequence.use_date_range = False
            if sequence.reset == 'enable':
                if sequence.reset_sequence == 'daily':
                    sequence.number_next_actual = 1
                    sequence.number_next = 1
                if sequence.reset_sequence == 'monthy':
                    if date.day == 1:
                        sequence.number_next = 1
                        sequence.number_next_actual = 1
                if sequence.reset_sequence == 'yearly':
                    if date.day == 1 and date.month == 1:
                        sequence.number_next = 1
                        sequence.number_next_actual = 1
