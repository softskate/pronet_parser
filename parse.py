from email.utils import parsedate_to_datetime
import imaplib
import email
import os
from uuid import uuid4
from database import Product, App, Crawl
import pandas as pd
from keys import EMAIL_ACCOUNT, EMAIL_PASSWORD


IMAP_SERVER = 'imap.ya.ru'
SAVE_FOLDER = 'prices'


class Parser:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    def save_attachment(self, part, folder):
        if not os.path.isdir(folder):
            os.makedirs(folder)
        filename = f'{uuid4()}.xls'
        if filename:
            filepath = os.path.join(folder, filename)
            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))
            return filepath


    def process_email_message(self, msg):
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            date_header = msg.get('Date')
            date_received = parsedate_to_datetime(date_header)

            filepath = self.save_attachment(part, SAVE_FOLDER)
            return self.parse(filepath, date_received)


    def start(self):
        complated = False
        self.mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        self.mail.select('inbox')

        # Поиск всех непрочитанных сообщений
        status, data = self.mail.search(None, 'UNSEEN')
        mail_ids = data[0].split()

        for mail_id in mail_ids:
            status, msg_data = self.mail.fetch(mail_id, '(RFC822)')
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = msg.get('subject', 'No Subject').strip()
            sender = msg.get('From')
            if subject == 'Юлия Короткова' or 'korotkovaya@pronetgroup.ru' in sender:
                data = self.process_email_message(msg)
                if data:
                    complated = True

        self.mail.logout()
        return complated


    def parse(self, file_path, datetime):
        df = pd.read_excel(file_path)
        df = df.where(pd.notna(df), None)
        row_data = df.iloc[9].tolist()

        translator = {
            'Код': 'productId',
            'Наименование': 'name',
            'Кол-во': 'qty',
            'Описание товара': 'description',
            'Производитель': 'brandName',
            'Цена рубли': 'price'
        }
        det_head = {}
        data = []
        headers = {}
        for n, cell in enumerate(row_data):
            if cell in translator:
                headers[n] = translator[cell]
            else:
                det_head[n] = cell

        appid = App.create(name='Pronet')
        crawlid = Crawl.create(created_at=datetime)
        category = ''
        for x, row in list(df.iterrows())[11:]:
            if not row.iloc[3]:
                category = row.iloc[1]
                continue
            row_data = {}
            details = {}
            for i in range(len(row)):
                if i in headers:
                    row_data[headers[i]] = row.iloc[i]
                
                elif i in det_head:
                    details[det_head[i]] = row.iloc[i]

            row_data['category'] = category
            row_data['details'] = details
            row_data['appid'] = appid
            row_data['crawlid'] = crawlid
            Product.create(**row_data)
            data.append(row_data)

        crawlid.finished = True
        crawlid.save()
        try: os.remove(file_path)
        except Exception as e: print("Error removing", e)
        return data
