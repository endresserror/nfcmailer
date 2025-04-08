import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
import nfc
from typing import cast
import re
import urllib.parse

FROM = '(送信元gmail)@gmail.com'  # 送信元メールアドレス
PASSWORD = ' '       # 送信元アカウントのパスワード
PORT = 587                          # メール送信ポート番号

BCC = ''  # BCC用の別宛先（必要に応じて設定）
SUBJECT = 'コンピュータクラブ入部登録フォーム'  # メールタイトル

# Googleフォームの基本URL (実際のフォームIDに置き換える必要があります)
FORM_BASE_URL = 'https://docs.google.com/forms/d/e/YOUR_FORM_ID_HERE/viewform'
# 学生IDを入力するフィールドのパラメータ名 (実際のフォームの項目名に合わせて調整)
STUDENT_ID_PARAM = 'entry.123456789'

# 正規表現パターンを一度だけコンパイル（高速化1）
STUDENT_NUM_PATTERN = re.compile(r'\d{2}[A-Z]{2,3}\d{3}')

# SMTP接続を保持するグローバル変数（高速化2）
smtp_connection = None

def create_mail(from_addr, to_addr, bcc_addr, subject, body):
    mail = MIMEText(body)
    mail["From"] = from_addr
    mail['To'] = to_addr
    mail['Bcc'] = bcc_addr
    mail['Subject'] = subject
    mail['Date'] = formatdate()
    return mail

def get_smtp_connection():
    """SMTP接続を取得または作成する（高速化2）"""
    global smtp_connection
    if smtp_connection is None:
        smtp_connection = smtplib.SMTP('smtp.gmail.com', PORT)
        smtp_connection.ehlo()
        smtp_connection.starttls()  # 暗号化
        smtp_connection.ehlo()
        smtp_connection.login(FROM, PASSWORD)  # アカウントにログイン
    return smtp_connection

def send_mail(to_addrs, mail):
    try:
        conn = get_smtp_connection()
        conn.sendmail(FROM, to_addrs, mail.as_string())  # 作成したメールを送信
    except Exception as e:
        # 接続エラーの場合、再接続を試みる
        global smtp_connection
        smtp_connection = None
        print(f"SMTP error: {e}, reconnecting...")
        conn = get_smtp_connection()
        conn.sendmail(FROM, to_addrs, mail.as_string())

def create_prefilled_form_url(student_id):
    """学籍番号が自動入力されたGoogleフォームのURLを作成する"""
    params = {STUDENT_ID_PARAM: student_id}
    query_string = urllib.parse.urlencode(params)
    return f"{FORM_BASE_URL}?{query_string}&usp=pp_url"

def on_connect(tag):
    sys_code = 0xFE00
    service_code = 0x1A8B
    idm, pmm = tag.polling(system_code=sys_code)
    tag.idm, tag.pmm, tag.sys = idm, pmm, sys_code
    sc = nfc.tag.tt3.ServiceCode(service_code >> 6, service_code & 0x3F)

    # 学籍番号を取得
    bc = nfc.tag.tt3.BlockCode(0, service=0)
    student_num = cast(bytearray, tag.read_without_encryption([sc], [bc]))
    student_num = student_num.decode("shift_jis")

    # 学籍番号を抽出（コンパイル済みの正規表現を使用）
    match = STUDENT_NUM_PATTERN.search(student_num)
    if match:
        extracted_student_num = match.group(0)
        print("学籍番号: " + extracted_student_num)

        # 学籍番号を使ってメールアドレスを生成
        to_addr = f"{extracted_student_num.lower()}@(任意のアドレス).com"
        print("送信先:", to_addr)

        # 学籍番号が自動入力されたGoogleフォームのURLを作成
        form_url = create_prefilled_form_url(extracted_student_num)
        
        # メール本文を作成
        body = f"""こんにちは、{extracted_student_num}さん。

への入部登録を開始するには、以下のリンクをクリックしてフォームに必要事項を入力してください。
学籍番号は自動で入力されています。

{form_url}

このメールは自動送信されています。返信は不要です。
"""
        # メールを作成して送信
        mail = create_mail(FROM, to_addr, BCC, SUBJECT, body)
        send_mail(to_addr, mail)
        print(f"入部フォームのURLを送信しました: {form_url}")
    else:
        print("学籍番号が見つかりません")
    return True

if __name__ == '__main__':
    try:
        print("学生証リーダーを起動しました。学生証をタッチしてください...")
        with nfc.ContactlessFrontend("usb") as clf:
            clf.connect(rdwr={"on-connect": on_connect})
    finally:
        # プログラム終了時にSMTP接続を閉じる（リソース管理）
        if smtp_connection:
            try:
                smtp_connection.close()
            except:
                pass
