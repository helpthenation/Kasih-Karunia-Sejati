# -*- coding: utf-8 -*-

from odoo import models, _
import StringIO
from odoo.tools.misc import xlsxwriter

class AccountReportContextCommon(models.TransientModel):
    _inherit = "account.report.context.common"

    def get_xlsx(self, response):
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        report_id = self.get_report_obj()
        sheet = workbook.add_worksheet(report_id.get_title())

        def_style = workbook.add_format({'font_name': 'Arial'})
        title_style2 = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_color': '#A001A2'})
        title_style2.set_font_size(14)
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_left = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_right = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1, 'font_color': '#FFFFFF',
             'num_format': '#,##0.00'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
        level_1_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
        level_1_style_right = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'num_format': '#,##0.00'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
        level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
        level_2_style_right = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2, 'num_format': '#,##0.00'})
        level_3_style = def_style
        level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
        level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2, 'num_format': '#,##0.00'})
        domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
        domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
        domain_style_right = workbook.add_format(
            {'font_name': 'Arial', 'italic': True, 'right': 2, 'num_format': '#,##0.00'})
        upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})

        # Set column widhts
        sheet.set_column(0, 0, 40)
        sheet.set_column(1, 2, 15)
        sheet.set_column(3, 7, 10)
        sheet.set_column(8, 9, 15)
        sheet.set_column(11, 12, 15)

        sheet.write(0, 0, self.env.user.company_id.partner_id.name, title_style2)
        sheet.write(1, 0, self.env.user.company_id.partner_id._display_address(without_company=True), title_style2)
        sheet.write(3, 0, report_id.get_title(), title_style2)

        y_offset = 5
        if self.get_report_obj().get_name() == 'coa' and self.get_special_date_line_names():
            sheet.write(y_offset, 0, '', title_style)
            sheet.write(y_offset, 1, '', title_style)
            x = 2
            for column in self.with_context(is_xls=True).get_special_date_line_names():
                sheet.write(y_offset, x, column, title_style)
                sheet.write(y_offset, x + 1, '', title_style)
                sheet.write(y_offset, x + 2, '', title_style)
                x += 2
            # sheet.write(y_offset, x, '', title_style)
            y_offset += 1

        x = 1
        sheet.write(y_offset, 0, 'Code / Account', title_style)
        for column in self.with_context(is_xls=True).get_columns_names():
            if len(column) == 2:
                sheet.write(y_offset, x, column[1].replace('<br/>', ' ').replace('&nbsp;', ' '), title_style)
                x += 2
            else:
                sheet.write(y_offset, x, column[0].replace('<br/>', ' ').replace('&nbsp;', ' '), title_style)
                x += 1
        y_offset += 1

        x = 0
        for due_column in self.with_context(is_xls=True).get_due_not_due_column_name():
            sheet.write(y_offset, x, due_column.replace('-', ' '), title_style)
            x += 1
        y_offset += 1

        lines = report_id.with_context(no_format=True, print_mode=True).get_lines(self)

        if self.partner_ids:
            filter_line = []
            for iline in lines:
                if iline.get('id') in self.partner_ids.ids or iline.get('partnerid') in self.partner_ids.ids:
                    filter_line.append(iline)
            lines = filter_line

        if lines:
            max_width = max([len(l['columns']) for l in lines])

        for y in range(0, len(lines)):
            if lines[y].get('type') == 'partner_id':
                lines[y]['columns'] = ['', ''] + lines[y]['columns']
            if lines[y].get('level') == 0 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[y].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            elif lines[y].get('type') != 'line':
                style_left = domain_style_left
                style_right = domain_style_right
                style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in xrange(1, max_width - len(lines[y]['columns']) + 1):
                sheet.write(y + y_offset, x, None, style)
            for x in xrange(1, len(lines[y]['columns']) + 1):
                if isinstance(lines[y]['columns'][x - 1], tuple):
                    lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    style.set_num_format('#,##0.00')
                    if lines[y] == 'o_account_reports_domain_total':
                        style.bold = True
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1], style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1], style_right)
            if lines[y]['type'] == 'total' or lines[y].get('level') == 0:
                for x in xrange(0, len(lines[0]['columns']) + 1):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in xrange(0, max_width + 1):
                sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
