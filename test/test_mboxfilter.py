# -*- coding: UTF-8 -*-
import email
import email.mime.text
import email.header
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
PERS_1  = 'Frank Heinrich W\xf6ller'
MAIL_1  = "fheini@woeller.de"
ADDR_1  = '"' + PERS_1 + '" <' + MAIL_1 + '>'
PERS_2  = 'Friederich Claus Sch\xfc\xdfler'
MAIL_2  = 'fclaus@schuessler.de'
ADDR_2  = '"' + PERS_2 + '" <' + MAIL_2 + '>'
MAIL_3  = 'anna-lisa@meissner-jakobi.de'
PERS_3  = 'Anna Lisa Mei\xdfner-Jakobi'
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

class MboxFilterOutput(mboxfilter.Filter):
  """ Test classes redirect output to stack unit."""
  def __init__(self, output=None, archive=False, indexing=False, filters=[], selectors=[], caching=False, separator="."):
    mboxfilter.Filter.__init__(self, output, archive, indexing, filters, selectors, caching, separator)
    self.unit = []

  def resultset_add(self, mail):
    """ append mail to a resultset by sort keys """
    if self.sort_keys_generate(mail) > 0:
      for key in self.sort_keys:
        self.unit.append((mail, key))
    else:
      self.unit.append((mail, None))

class MboxFilterOutputIntegrity(MboxFilterOutput):
  def error(self, exc, mail):
    self.unit.append((mail, exc[0])) 

class TestMboxFilter(unittest.TestCase):
  def __init__(self, nop):
    unittest.TestCase.__init__(self, nop)
    shutil.rmtree(DIR, True)
    os.mkdir(DIR)
    self.mbox1()

  def test_header_value_formatted(self):
    fil = mboxfilter.Filter()	   
    self.assertEqual(MAIL_1, mboxfilter.header_value_formatted('From', None, ADDR_1))
    self.assertEqual(MAIL_5, mboxfilter.header_value_formatted('From', None, ADDR_5))

  #def test_header_decode(self):
  #  fil = mboxfilter.Filter()                                                               
  #  self.assertEqual(fil.header_strip(ADDR_2, '"') + ', '+ MAIL_3.decode('iso-8859-1'), fil.header_decode('''=?utf-8?Q?Friederich_Claus_Sch=C3=BC=C3=9Fler?= <fclaus@schuessler.de>,
  #anna-lisa@meissner-jakobi.de'''))

  def test_no_filter(self):
    fil = MboxFilterOutput()
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results_defaults(m, fil.unit)

  def test_one_filter(self):
    fil = MboxFilterOutput(filters=[("From", PERS_1)])
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results_defaults([m[0], m[1]], fil.unit)

  def test_two_filter(self):
    fil = MboxFilterOutput(filters=[("From", PERS_1), ("From", PERS_2)])
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results_defaults([m[1]], fil.unit)

  def test_many_filter(self):
    fil = MboxFilterOutput(filters=[("From", PERS_1), ("To", PERS_3), ("Message-ID", MSGID_2)])
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results_defaults([m[1]], fil.unit)

  def test_date_sort(self):
    fil = MboxFilterOutput(selectors=[("Date", "%Y")])
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results_defaults(m, fil.unit, str(2013))
  
  def test_from_sort(self):
    fil = MboxFilterOutput(selectors=[("From", None)])
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results([(m[0], MAIL_1), (m[1], MAIL_1), (m[1], MAIL_2), (m[2], MAIL_3), (m[3], MAIL_2), (m[4], MAIL_4), (m[5], MAIL_4)], fil.unit)
    
  def test_from_to_sort(self):
    fil = MboxFilterOutput(selectors=[("From", None), ("To", None)])
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results([(m[0], MAIL_1+"."+MAIL_2), (m[1], MAIL_1+"."+MAIL_3), (m[1], MAIL_2+"."+MAIL_3), (m[2], MAIL_3+"."+MAIL_2), (m[2], MAIL_3+"."+MAIL_1)], fil.unit)

  def test_from_filter_from_sort(self):
    fil = MboxFilterOutput(selectors=[("From", None)], filters=[("From", PERS_1)])
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results([(m[0], MAIL_1), (m[1], MAIL_1)], fil.unit)
  
  def test_from_to_sort(self):
    fil = MboxFilterOutput(filters=[("From", PERS_1), ("To", PERS_3)], selectors=[("From", None), ("Date", "%a")])
    fil.filter_mbox(MBOX_1)
    m = mailbox.mbox(MBOX_1)
    self.check_results([(m[1], MAIL_1+".Sun")], fil.unit)

  def test_archive(self):
   fil = MboxFilterOutput(output="unit-tests", archive=True)
   fil.filter_mbox(MBOX_1)	  

  def test_caching(self):
    fil_1 = mboxfilter.Filter(caching=True, filters=[("From", PERS_1)])
    fil_2 = mboxfilter.Filter(caching=True, filters=[("To", PERS_1)])    
    fil_3 = MboxFilterOutput(output="unit-tests", selectors=[("Date", "%Y")])
    fil_1.filter_mbox(MBOX_1)
    fil_2.filter_mbox(MBOX_1)
    fil_3.filter_mbox(fil_1.cache + fil_2.cache)
    m = mailbox.mbox(MBOX_1)
    self.check_results([(m[0], "2013"), (m[1], "2013"), (m[2], "2013"), (m[3], "2013"), (m[4], "2013"), (m[5], "2013")], fil_3.unit)

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
    self.assertEqual(len(shld), len(res), "leaking results ")
    for i in range(0, len(shld)):
      self.assertTrue(str(shld[i][0]) == str(res[i][0]))
      if (shld[i][1] is not None):
	    # todo check results
        self.assertTrue(self.decode_python(shld[i][1]) == res[i][1])

  def decode_python(self, strg):
    """ Decodes a string if neccessary """
    try: # python 2.6, 2.7
      return strg.decode('iso-8859-1')
    except: # pyhton 3
      return strg

  def mbox1(self):
    """ Create a mbox for testing """
    m = mailbox.mbox(MBOX_1)
    m.add(self.mail(From=[ADDR_1], To=[ADDR_2], Message_ID=MSGID_1, Date=DATE_1))
    m.add(self.mail(From=[ADDR_1, ADDR_2], To=[ADDR_3], Message_ID=MSGID_2, Date=DATE_2))
    m.add(self.mail(From=[ADDR_3], To=[ADDR_2, ADDR_1], Message_ID=MSGID_3, Date=DATE_3))
    m.add(self.mail(From=[ADDR_2], To=[ADDR_1], Message_ID=MSGID_4, Date=DATE_4))
    m.add(self.mail(From=[ADDR_4], To=[ADDR_1, ADDR_2], Message_ID=MSGID_5, Date=DATE_5))
    m.add(self.mail(From=[ADDR_4], To=[ADDR_1, ADDR_2], Message_ID=MSGID_5, Date=DATE_5))
    m.flush()
 
  def mail(self, From=[ADDR_1], To=[ADDR_2], Cc=[ADDR_3], Bcc=[ADDR_4], Date=None, Subject=[SUBJ], Body=BODY, Message_ID=MSGID_1):
    """ Create a mail """
    mail = email.mime.text.MIMEText(Body)
    mail['From'] =  self.header_encode(From)
    mail['To']   =  self.header_encode(To)
    mail['Cc']   =  self.header_encode(From)
    mail['Bcc']  =  self.header_encode(From)
    mail['Subject'] = self.header_encode(Subject)
    mail['Date'] = Date
    mail['Message-ID'] = '<' + Message_ID + '>'
    return mail	  

  def header_encode(self, headers):
    """ Encode a header value in ISO-8859-1 """
    return email.header.Header(", ".join(headers), 'iso-8859-1')
	          
if __name__ == '__main__':
  unittest.main()