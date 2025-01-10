import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
import nfc
from typing import cast
import re

FROM = '(送信元gmail)@gmail.com'  # 送信元メールアドレス
PASSWORD = ' '       # 送信元アカウントのパスワード
PORT = 587                          # メール送信ポート番号

BCC = ''  # BCC用の別宛先（必要に応じて設定）
SUBJECT = 'Welcome To Computer Club'  # メールタイトル
BODY = '''ここのメッセージを書いて下さい'''


def create_mail(from_addr, to_addr, bcc_addr, subject, body):  # メール作成メソッド
    mail = MIMEText(body)
    mail["From"] = from_addr
    mail['To'] = to_addr
    mail['Bcc'] = bcc_addr
    mail['Subject'] = subject
    mail['Date'] = formatdate()
    return mail


def send_mail(to_addrs, mail):  # メール送信メソッド
    smtpobj = smtplib.SMTP('smtp.gmail.com', PORT)
    smtpobj.ehlo()
    smtpobj.starttls()  # 暗号化
    smtpobj.ehlo()
    smtpobj.login(FROM, PASSWORD)  # アカウントにログイン
    smtpobj.sendmail(FROM, to_addrs, mail.as_string())  # 作成したメールを送信
    smtpobj.close()


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

    # 学籍番号を抽出（2~3文字の学科コードに対応）
    match = re.search(r'\d{2}[A-Z]{2,3}\d{3}', student_num)
    if match:
        extracted_student_num = match.group(0)
        print("student number : " + extracted_student_num)

        # 学籍番号を使ってメールアドレスを生成
        to_addr = f"{extracted_student_num.lower()}@(任意のアドレス).com"
        print("Sending email to:", to_addr)

        # メールを作成して送信
        mail = create_mail(FROM, to_addr, BCC, SUBJECT, BODY)
        send_mail(to_addr, mail)
    else:
        print("学籍番号が見つかりません")


if __name__ == '__main__':
    with nfc.ContactlessFrontend("usb") as clf:
        clf.connect(rdwr={"on-connect": on_connect})
