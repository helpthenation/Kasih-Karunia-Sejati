import xlwt
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx


class SalePersonPrint(ReportXlsx):

    def generate_xlsx_report(self, workbook, data,wiz):


        main_heading_format = workbook.add_format({'align': 'center',
                                              'valign': 'vcenter',
                                              'bold': True, 'size': 16})

        heading_format = workbook.add_format({'align': 'center',
                                              'valign': 'vcenter',
                                              'bold': True, 'size': 14})

        sub_heading_format = workbook.add_format({'align': 'center',
                                                  'valign': 'vcenter',
                                                  'bold': True, 'size': 12})
        bold = workbook.add_format({'bold': True})
        worksheet = workbook.add_worksheet("Product Balance Report")
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:E', 25)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 15)

        # worksheet.set_column('U:U', 30)
        end_col = 17
        workbook = xlwt.Workbook()
        worksheet.merge_range(0, 0, 1, 4, wiz.name, main_heading_format)
        worksheet.write(3, 0, 'Inventoried Location', sub_heading_format)
        worksheet.write(3, 1, 'Inventory of', sub_heading_format)
        worksheet.write(3, 2, 'Inventory Date', sub_heading_format)
        worksheet.write(3, 3, 'Adjustment type', sub_heading_format)
        worksheet.write(3, 4, 'Force Accounting Date', sub_heading_format)
        row=4
        for stock in wiz:
            worksheet.write(row, 0, stock.location_id.location_id.name)
            worksheet.write(row, 1, stock.filter)
            worksheet.write(row, 2, stock.date)
            worksheet.write(row, 3, stock.adjustment_type.name)
            worksheet.write(row, 4, stock.accounting_date)
            row += 1


        worksheet.merge_range(8, 0, 9, 2, 'Inventory Details', heading_format)
        # worksheet.merge_range('A:S',"Sale Report(Based On Sales Rep)", heading_format)
        worksheet.write(10, 0, 'Product', sub_heading_format)
        worksheet.write(10, 1, 'Location', sub_heading_format)
        worksheet.write(10, 2, 'Theoretical Quantity', sub_heading_format)
        worksheet.write(10, 3, 'Theoretical Amount', sub_heading_format)
        worksheet.write(10, 4, 'Actual Quantity', sub_heading_format)
        worksheet.write(10, 5, 'Actual Amount', sub_heading_format)
        worksheet.write(10, 6, 'Changes', sub_heading_format)
        row =11


        for stock in wiz.line_ids:
            worksheet.write(row, 0, stock.product_name)
            worksheet.write(row, 1, stock.inventory_location_id.location_id.name    )
            worksheet.write(row, 2, stock.theoretical_qty)
            worksheet.write(row, 3, stock.theoritical_amount)
            worksheet.write(row, 4, stock.product_qty)
            worksheet.write(row, 5, stock.real_amount)
            worksheet.write(row, 6, stock.change)
            row += 1


SalePersonPrint('report.stock.inventory.xlsx',
                    'stock.inventory')