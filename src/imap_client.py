
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
import os
import datetime
import hashlib
import re

class EmailFetcher:
    def __init__(self, user, password, label):
        self.user = user
        self.password = password
        self.label = label
        self.mail = None

    def connect(self):
        print("Connecting to Gmail...")
        self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
        self.mail.login(self.user, self.password)
        rv, _ = self.mail.select(f'"{self.label}"')
        if rv != 'OK':
            raise Exception(f"Label {self.label} not found")

    def search_all(self):
        status, messages = self.mail.search(None, 'ALL')
        if not messages[0]:
            return []
        return messages[0].split()

    def fetch_headers(self, email_ids):
        """
        Fetch basic headers for synchronization (Phase 1)
        Returns: Dict {deterministic_id: valid_msg_num}
        """
        email_map = {}
        for num in email_ids:
            try:
                status, msg_data = self.mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT)])')
                msg_header = email.message_from_bytes(msg_data[0][1])
                subject = self.get_decoded_subject(msg_header)
                clean_subj = self._clean_subject_prefixes(subject)
                f_id = self._get_deterministic_id(clean_subj)
                email_map[f_id] = num
            except: pass
        return email_map

    def fetch_full_message(self, num):
        status, msg_data = self.mail.fetch(num, '(RFC822)')
        return email.message_from_bytes(msg_data[0][1])

    def close(self):
        if self.mail:
            self.mail.close()
            self.mail.logout()

    # --- HELPERS ---
    @staticmethod
    def get_decoded_subject(msg):
        subject_header = msg.get("Subject", "")
        if not subject_header: return "Untitled"
        decoded_list = decode_header(subject_header)
        full_subject = ""
        for part, encoding in decoded_list:
            if isinstance(part, bytes):
                full_subject += part.decode(encoding or "utf-8", errors="ignore")
            else:
                full_subject += str(part)
        return full_subject.strip()

    def _clean_subject_prefixes(self, subject):
        if not subject: return "Untitled"
        pattern = r'^\s*\[?(?:Fwd|Fw|Tr|Re|Aw|Wg)\s*:\s*\]?\s*'
        cleaned = subject
        while re.match(pattern, cleaned, re.IGNORECASE):
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _get_deterministic_id(self, subject):
        if not subject: subject = "sans_titre"
        hash_object = hashlib.sha256(subject.encode('utf-8', errors='ignore'))
        return hash_object.hexdigest()[:12]
