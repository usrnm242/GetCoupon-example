import imaplib
import json

from parsers import MailParser
import constants


def _connect_imap():
    mail = imaplib.IMAP4_SSL('imap.mail.ru')
    mail.login('', "")
    return mail


def run_mail_parser() -> list:
    mail_folders = ("INBOX", "INBOX/Newsletters",)
    mail_indices_file = constants.email_read_msg

    packed_info = []  # for returning

    mail = _connect_imap()

    with open(mail_indices_file, 'r') as f:
        read_old_indices: dict = json.load(f)

    for folder in mail_folders:
        mail.select(folder)
        status, raw_numerated_mails = mail.search(None, 'ALL')
        raw_numerated_mails: bytes = raw_numerated_mails[0]  # b'1 2 3 4 5 6 7'
        all_numerated_mails = set(map(
            int, raw_numerated_mails.decode('utf-8').split(' ')
        ))

        old_indices = set(read_old_indices[folder])

        new_mails_indices = all_numerated_mails - old_indices

        for mail_id in new_mails_indices:
            mail_id = bytes(str(mail_id), encoding='utf-8')
            status, data = mail.fetch(mail_id, '(RFC822)')
            raw_email = data[0][1]
            try:
                promocodes, shop, category = \
                    MailParser(raw_email).extract_info()

                packed_info.append([promocodes, shop, category])

            except (AttributeError, UnicodeDecodeError):
                continue

            except Exception as e:
                print(e, folder, mail_id)
                continue

            for p in promocodes:
                print(p.coupon, shop.name, shop.websiteLink)

        read_old_indices[folder] = list(all_numerated_mails)

    with open(mail_indices_file, 'w') as f:
        # all_numerated_mails
        json.dump(read_old_indices, f, ensure_ascii=False, indent=1)

    mail.close()
    mail.logout()

    return packed_info


if __name__ == '__main__':
    def __clear_indices():
        import json
        with open('', 'w') as f:
            json.dump({"INBOX": [], "INBOX/Newsletters": []}, f, ensure_ascii=False, indent=2)

    __clear_indices()
    print("kek")
    run_mail_parser()
