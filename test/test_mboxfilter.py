# -*- coding: UTF-8 -*-
import email
import email.mime.application
import email.mime.text
import email.mime.image
import email.mime.multipart
import email.header
import io
import mailbox
import mboxfilter
import os
import re
import shutil
import sys
import unittest

SUBJ    = 'L\xf6rem ips\xfcm dolor sit amet'
BODY    = 'Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy  eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam  nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.'
DATE_1  = 'Friday, 21 June 2013 12:15:00 +0200'
DATE_2  = 'Sunday, 23 June 2013 07:15:22 +0200'
DATE_3  = 'Tuesday, 25 June 2013 18:41:49 +0300'
DATE_4  = 'Wednesday, 26 June 2013 18:42:00 +0000'
DATE_5  = 'Friday, 28 June 2013 03:13:59 +0200'
MSGID_1 = 'mssgid-1'
MSGID_2 = 'mssgid-2'
MSGID_3 = 'mssgid-3'
MSGID_4 = 'mssgid-4'
MSGID_5 = 'mssgid-5'
DIR     = 'unit-tests'
PERS_1  = 'Frank Heinrich W\xf6ller' #TODO Name, Ph.d
MAIL_1  = "fheini@woeller.de"
ADDR_1  = '"' + PERS_1 + '" <' + MAIL_1 + '>'
PERS_2  = 'Friederich Claus Sch\xfc\xdfler'
MAIL_2  = 'FClaus@Schuessler.de'
ADDR_2  = '"' + PERS_2 + '" <' + MAIL_2 + '>'
MAIL_3  = 'anna-lisa@meissner-jakobi.de'
PERS_3  = 'Anna Lisa Mei\xdfner-Jakobi, Fr'
ADDR_3  = '"' + PERS_3 + '" <' + MAIL_3 + '>'
PERS_4  = 'Jos\xe9 Carlos García Fuentes'
MAIL_4  = 'jose@garcia.es'
ADDR_4  = '"' + PERS_4 + '" <' + MAIL_4 + '>'
PERS_5  = ''
MAIL_5  = 'spammer@ugly.org'
ADDR_5  = MAIL_5
MBOX    = DIR + '/' + 'mbox'
MBOX_1  = MBOX + '_1'
MBOX_2  = MBOX + '_2'
MBOX_3  = MBOX + '_3'

ERROR_DATE_NOT_FOUND = 'header not found: Date'
ERROR_FROM_NOT_FOUND = 'header not found: From'
ERROR_CANT_ADD_TWICE = "can't add mail twice to result index" 
class MboxFilterOutput(mboxfilter.Filter):
	""" Test classes redirect output to stack unit."""
	def __init__(self, output=".", archive=False, indexing=False, filters=[], selectors=[], caching=False, separator=".", failures=None, export_payload=False, reduce_payload=False, payload_exportpath="./", quiet=True):
		mboxfilter.Filter.__init__(self, output, archive, indexing, filters, selectors, caching, separator, failures, export_payload, reduce_payload, payload_exportpath, quiet)
		self.unit = []
		self.unit_failures = []

	def resultset_pipe(self, key, mail):
		self.unit.append((mail, key))

	def error(self, msg, mail):
		self.unit_failures.append((mail, msg))

class MboxFilterOutputIntegrity(MboxFilterOutput):
	def error(self, exc, mail):
		self.unit.append((mail, exc[0])) 

class UnkownFileTypeError(Exception):
	def __init__(self, ftype):
		self.ftype = ftype

	def __str__(self):
		return "File type: %s not kown" %self.ftyp

class TestMboxFilter(unittest.TestCase):
	def __init__(self, nop):
		unittest.TestCase.__init__(self, nop)
		shutil.rmtree(DIR, True)
		os.mkdir(DIR)
		self.mbox1()

	def test_header_format(self):
		fil = mboxfilter.Filter(quiet=True)	   
		self.assertEqual(MAIL_1, mboxfilter.header_format('From', ADDR_1))
		self.assertEqual(MAIL_5, mboxfilter.header_format('From', ADDR_5))

	def test_archive(self):
		fil = MboxFilterOutput(output="unit-tests", archive=True)
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)	  
		self.check_results([(m[5], ERROR_CANT_ADD_TWICE), (m[6], ERROR_DATE_NOT_FOUND)], fil.unit_failures)

	def test_no_filter(self):
		fil = MboxFilterOutput(selectors=[]) # python error!! 
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results_defaults(m, fil.unit)
		self.check_results_defaults([], fil.unit_failures)

	def test_one_filter(self):
		fil = MboxFilterOutput(filters=[("From", PERS_1)])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results_defaults([m[0], m[1]], fil.unit)
		self.check_results([(m[6], ERROR_FROM_NOT_FOUND)], fil.unit_failures)

	def test_two_filter(self):
		fil = MboxFilterOutput(filters=[("From", PERS_1), ("From", PERS_2)])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results_defaults([m[1]], fil.unit)
		self.check_results([(m[6], ERROR_FROM_NOT_FOUND)], fil.unit_failures)

	def test_many_filter(self):
		fil = MboxFilterOutput(filters=[("From", PERS_1), ("To", PERS_3), ("Message-ID", MSGID_2)])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results_defaults([m[1]], fil.unit)
		self.check_results([(m[6], ERROR_FROM_NOT_FOUND)], fil.unit_failures)

	def test_date_sort(self):
		fil = MboxFilterOutput(selectors=[("Date", "%Y")])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results_defaults([m[0], m[1], m[2], m[3], m[4], m[5]], fil.unit, str(2013))
		self.check_results([(m[6], ERROR_DATE_NOT_FOUND)], fil.unit_failures)

	def test_from_sort(self):
		fil = MboxFilterOutput(selectors=[("From", None)])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results([(m[0], MAIL_1), (m[1], MAIL_1), (m[1], MAIL_2), (m[2], MAIL_3), (m[3], MAIL_2), (m[4], MAIL_4), (m[5], MAIL_4)], fil.unit)
		self.check_results([(m[6], ERROR_FROM_NOT_FOUND)], fil.unit_failures)
  
	def test_from_to_sort(self):
		fil = MboxFilterOutput(selectors=[("From", None), ("To", None)])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results([(m[0], MAIL_1+"."+MAIL_2), (m[1], MAIL_1+"."+MAIL_3), (m[1], MAIL_2+"."+MAIL_3), (m[2], MAIL_3+"."+MAIL_2), (m[2], MAIL_3+"."+MAIL_1), (m[3], MAIL_2+"."+MAIL_1), (m[4], MAIL_4+"."+MAIL_1), (m[4], MAIL_4+"."+MAIL_2), (m[5], MAIL_4+"."+MAIL_1), (m[5], MAIL_4+"."+MAIL_2)], fil.unit)
		self.check_results([(m[6], ERROR_FROM_NOT_FOUND)], fil.unit_failures)#

	def test_from_filter_from_sort(self):
		fil = MboxFilterOutput(selectors=[("From", None)], filters=[("From", PERS_1)])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results([(m[0], MAIL_1), (m[1], MAIL_1)], fil.unit)
		self.check_results([(m[6], ERROR_FROM_NOT_FOUND)], fil.unit_failures)

	def test_from_to_sort(self):
		fil = MboxFilterOutput(filters=[("From", PERS_1), ("To", PERS_3)], selectors=[("From", None), ("Date", "%a")])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox(MBOX_1)
		self.check_results([(m[1], MAIL_1+".Mon")], fil.unit)
		self.check_results([(m[6], ERROR_FROM_NOT_FOUND)], fil.unit_failures)

	def test_payload(self):
		fil = MboxFilterOutput(filters=[("From", PERS_1), ("To", PERS_2)], export_payload=True, reduce_payload=True, payload_exportpath="unit-tests")
		fil.filter_mbox(MBOX_1)
		self.assertEqual(file_read("test.txt"), file_read("unit-tests/mssgid-1.01.test.txt"))
		self.assertEqual(file_read("test.png"), file_read("unit-tests/mssgid-1.02.test.png"))
		self.assertEqual(file_read("test.odt"), file_read("unit-tests/mssgid-1.03.test.odt"))
		self.assertEqual(file_read("test.pdf"), file_read("unit-tests/mssgid-1.04.test.pdf"))
		self.assertEqual(1, len(fil.unit[0][0].get_payload()))

	def test_caching(self):
		fil_1 = mboxfilter.Filter(caching=True, filters=[("From", PERS_1)], export_payload=True, quiet=True)
		fil_1.filter_mbox(MBOX_1)
		fil_2 = mboxfilter.Filter(caching=True, filters=[("To", PERS_1)], quiet=True)    
		fil_2.filter_mbox(MBOX_1)
		fil_3 = MboxFilterOutput(output="unit-tests", selectors=[("Date", "%Y")])
		fil_3.filter_mbox(fil_1.passed_mails + fil_2.passed_mails)
		m = mailbox.mbox(MBOX_1)
		self.check_results([(m[0], "2013"), (m[1], "2013"), (m[2], "2013"), (m[3], "2013"), (m[4], "2013"), (m[5], "2013")], fil_3.unit)

	def test_components(self):
		fil_1 = mboxfilter.Filter(caching=True, filters=[("From", PERS_1)], export_payload=True, quiet=True)
		fil_1.filter_mbox(MBOX_1)
		self.assertEqual(file_read("test.txt"), fil_1.exported_payloads[0])
		self.assertEqual(file_read("test.png"), fil_1.exported_payloads[1])
		self.assertEqual(2, fil_1.passed)
		self.assertEqual(len(fil_1.passed_mails), fil_1.passed)
		self.assertEqual(7, fil_1.filtered)
		m = mailbox.mbox(MBOX_1)
		self.assertEqual(str(m[0]), str(fil_1.passed_mails[0]))
		self.assertEqual(str(m[0]), str(fil_1.resultset[None][0]))

	"""  
	def test_subject_sort(self):
		fil = MboxFilterOutput(selectors=[("Subject", None)])
		fil.filter_mbox(MBOX_1)
		m = mailbox.mbox[MBOX_1]
		self.check_results([(m[0], MAIL_1), (m[1], MAIL_1), (m[1], MAIL_2), (m[2], MAIL_3), (m[3], MAIL_2), (m[4], MAIL_4), (m[5], MAIL_4)], fil.unit)
	"""

	def check_results_defaults(self, shld, res, default=None):
		self.check_results([(value, default) for value in shld], res)

	def check_results(self, shld, res):
		""" Compare a list of results to """
		self.assertEqual(len(shld), len(res), "leaking results ")
		for i in range(0, len(res)):
			if i < len(shld):
				self.assertTrue(str(shld[i][0]) == str(res[i][0]))
			if (shld[i][1] is not None):
				# todo check results
				self.assertTrue(self.decode(shld[i][1]) == res[i][1])

	def decode(self, strg):
		""" Decodes a string if neccessary """
		if type(strg) is bytes:
			return strg.decode("ISO-8859-1")
		return strg

	def mbox1(self):
		""" Create a mbox for testing """
		m = mailbox.mbox(MBOX_1)
		m.add(self.mail(frm=[ADDR_1], to=[ADDR_2], mid=MSGID_1, date=DATE_1, payloads=["test.txt", "test.png", "test.odt", "test.pdf"]))
		m.add(self.mail(frm=[ADDR_1, ADDR_2], to=[ADDR_3], mid=MSGID_2, date=DATE_2))
		m.add(self.mail(frm=[ADDR_3], to=[ADDR_2, ADDR_1], mid=MSGID_3, date=DATE_3))
		m.add(self.mail(frm=[ADDR_2], to=[ADDR_1], mid=MSGID_4, date=DATE_4))
		m.add(self.mail(frm=[ADDR_4], to=[ADDR_1, ADDR_2], mid=MSGID_5, date=DATE_5))
		m.add(self.mail(frm=[ADDR_4], to=[ADDR_1, ADDR_2], mid=MSGID_5, date=DATE_5))
		m.add(self.mail())
		m.flush()

	def mail(self, frm=None, to=None, date=None, subject=None, body=BODY, mid=None, payloads=[]):
		""" Create a mail """
		if len(payloads) > 0:
			mail = email.mime.multipart.MIMEMultipart()
			mail.attach(email.mime.text.MIMEText(body))
			for payload in payloads:
				self.mail_attach(mail, payload)
		else:
			mail = email.mime.text.MIMEText(body)
		return self.mail_header(mail, frm, to, date, subject, mid)

	def mail_attach(self, mail, payload):
		""" Attach a plain text file """
		pld = file_read(payload)
		ext = os.path.splitext(payload)[1]
		if ext == ".txt":
			msg = email.mime.text.MIMEText(self.decode(pld), "plain")
		elif ext == ".png":
			msg = email.mime.image.MIMEImage(pld, "png")
		elif ext == ".pdf":
			msg = email.mime.application.MIMEApplication(pld, "pdf")
		elif ext == ".odt":
			msg = email.mime.application.MIMEApplication(pld, "odt")
		else:
			raise UnkownFileTypeError(ext)
		msg.add_header("Content-Disposition", 'attachment', filename=payload)
		mail.attach(msg)

	def mail_header(self, mail, frm, to, date, subject, mid):
		""" Define mail header """
		if frm:
			mail['From'] =  self.header_encode(frm)
		if to:
			mail['To']   =  self.header_encode(to)
		if subject:
			mail['Subject'] = self.header_encode(subject)
		if date:
			mail['Date'] = date
		if mid:
			mail['Message-ID'] = '<' + mid + '>'
		return mail	  
		
	def header_encode(self, headers):
		""" Encode a header value in ISO-8859-1 """
		return email.header.Header(", ".join(headers), 'iso-8859-1')

def file_read(path):
	with open(path, "rb") as fd:
		return fd.read()
	          
if __name__ == '__main__':
	unittest.main()