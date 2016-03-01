import xlsxwriter
import datetime
import io


def convert_xls_head(column_list, column_labels):
    return [column_labels.get(column_list[item]) for item in range(0, len(column_list))]


def write_xls(column_labels, column_list, value, sheet_name="Sheet1"):
    head_line = convert_xls_head(column_list, column_labels)

    rv = io.BytesIO()
    xls = xlsxwriter.Workbook(rv)
    sheet = xls.add_worksheet(sheet_name)
    # 第一行标题
    for i in range(0, len(head_line)):
        sheet.write(0, i, head_line[i])
    # 写入内容

    for row in range(0, len(value)):
        for cols in range(0, len(column_list)):
            row_value = getattr(value[row], column_list[cols])
            if isinstance(row_value, datetime.datetime):
                row_value = row_value.strftime('%Y年%m月%d日 %H:%M:%S')
            elif row_value is None:
                row_value = ''
            else:
                row_value = str(row_value)
            sheet.write(row + 1, cols, row_value)
    xls.close()
    rv.seek(0)
    return rv.read()


def export_xls(column_list, column_labels, column_values):
    return write_xls(column_labels, column_list, value=column_values)
