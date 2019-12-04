# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import base64
import xlwt
from StringIO import StringIO


class PartnerExport(models.TransientModel):
    _name = 'bom.export.wizard'

    @api.multi
    def print_report_customer_info_xls(self):
        filename = 'bom.export.wizard.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet('Patients Info')
        style = xlwt.easyxf('font:height 200, bold True, name Arial;align: horiz center;'
                            'borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left medium, right medium, top medium, bottom medium;')

        if self.env.context and self.env.context.get('active_ids'):
            bom_ids = self.env['mrp.bom'].sudo().search([('id', 'in', self.env.context.get('active_ids'))])

            worksheet.write(0, 0, 'Product', style)
            worksheet.write(0, 1, 'QTY', style)
            worksheet.write(0, 2, 'Uom', style)
            worksheet.write(0, 3, 'Materials Reference Code', style)
            worksheet.write(0, 4, 'Materials', style)
            worksheet.write(0, 5, 'Materials Qty', style)
            worksheet.write(0, 6, 'UOM', style)
            worksheet.write(0, 7, 'Routing', style)

            worksheet.col(0).width = 6000
            worksheet.col(1).width = 6000
            worksheet.col(2).width = 6000
            worksheet.col(3).width = 9000
            worksheet.col(4).width = 9000
            worksheet.col(5).width = 9000
            row = 1

            for bom in bom_ids:
                column = 0

                if bom.bom_line_ids:
                    for bom_line in bom.bom_line_ids:

                        worksheet.write(row, column, bom.product_tmpl_id.name or '')
                        worksheet.write(row, column + 1, bom.product_qty or '')
                        worksheet.write(row, column + 2, bom.product_uom_id.name or '')
                        worksheet.write(row, column + 3, bom_line.product_id.default_code or '')
                        worksheet.write(row, column + 4, bom_line.product_id.name or '')
                        worksheet.write(row, column + 5, bom_line.product_qty or '')
                        worksheet.write(row, column + 6, bom_line.product_uom_id.name or '')
                        worksheet.write(row, column + 7, bom.routing_id.name or '')
                        row += 1
                else:

                    worksheet.write(row, column, bom.product_tmpl_id.name or '')
                    worksheet.write(row, column + 1, bom.product_qty or '')
                    worksheet.write(row, column + 2, bom.product_uom_id.name or '')
                    worksheet.write(row, column + 7, bom.routing_id.name or '')
                    row += 1
            #
            #     worksheet.write(row, column + 3, one_patient.street or '')
            #     worksheet.write(row, column + 4, one_patient.street2 or '')
            #     worksheet.write(row, column + 5, '')
            #     worksheet.write(row, column + 6, one_patient.zip or '')
            #     worksheet.write(row, column + 7, one_patient.city or '')
            #     worksheet.write(row, column + 8, one_patient.country_id and one_patient.country_id.name or '')
            #
            #

            fp = StringIO()
            workbook.save(fp)
            export_id = self.env['excel.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename})
            fp.close()
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'res_model': 'excel.extended',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': self._context,
                'target': 'new',
            }



