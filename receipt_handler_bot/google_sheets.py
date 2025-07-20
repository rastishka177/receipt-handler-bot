import gspread
from google.oauth2.service_account import Credentials
from receipt_handler_bot.config import GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SPREADSHEET_ID
from openpyxl import Workbook
# Авторизация
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file(
    GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
client = gspread.authorize(creds)

# Получаем таблицу
spreadsheet = client.open_by_key(GOOGLE_SPREADSHEET_ID)

def add_receipt(sheet_name, data: list):
    """
    Добавляет строку в лист Google таблицы
    :param sheet_name: название листа (например, 'Администрация')
    :param data: список данных (по колонкам)
    """
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        sheet.append_row(data, value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"Ошибка при добавлении в Google Sheets: {e}")

def get_report(sheet_name):
    """
    Получает все данные из листа (для формирования отчета)
    """
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        return sheet.get_all_records()
    except Exception as e:
        print(f"Ошибка при получении данных из Google Sheets: {e}")
        return []

def get_receipts_for_department(department):
    # Получаем таблицу
    spreadsheet = client.open(GOOGLE_SERVICE_ACCOUNT_FILE)
    try:
        worksheet = spreadsheet.worksheet(department)
    except gspread.exceptions.WorksheetNotFound:
        return None
    return worksheet.get_all_values()

def generate_report_excel(department, file_path):
    data = get_receipts_for_department(department)
    if not data:
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = department
    for row in data:
        ws.append(row)
    wb.save(file_path)
    return True