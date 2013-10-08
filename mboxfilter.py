"""
Filter and sort mails from mboxes for archiving and reporting
"""
import dateutil
import dateutil.parser
import getopt
import hashlib
import email
import email.generator
import mailbox
import os
import re
import sqlite3
import sys
import traceback # todo remove

__version__ = "0.1.2"

# Default encoding of emails:
EMAIL_ENCO = "ISO-8859-15"
# Deafult date format
DATE_FORMAT = "%Y"

class Filter:
  # Output files to directory:
  output = "./"
  # Filname of index database:
  resultset_index = "index.sqlite3"
  # Number of passed mails:
  passed = 0
  # Number of filtered mails:
  filtered = 0
  # Do sorting by default:
  sort_date_default = DATE_FORMAT
  # Do indexing by default:
  indexing = False
  # Keep filter matches in List:
  filter_matches = []
  # Keep sort keys in list:
  sort_keys = []  
  
  def __init__(self, output=None, archive=False, indexing=False, filters=[], selectors=[], caching=False, separator="."):
    """ Initialize a Filter object.
      output
        files are outputed into directory
        
      archive
        use default sorting and indexeing
        
      indexing
        import mail headers into result index database named index.sqlite3 table mails. duplets are revoked.
        
      filters
         List of tuples, e.g. ("From", regexp), ("To", regexp) or ("Date", format)
         
      selectors
         List of tuples, e.g. ("From", None), ("To", None), ("Date", format). mails will be output to files.

      caching
        cache resultset. Disables output and indexing
      
      separator
        separates key parts
    """
    self.output = output or "."
    self.archive = archive
    self.filters = filters
    self.selectors = selectors
    if self.archive and len(self.selectors) == 0:
      self.selectors.append(("Date", self.sort_date_default))
    if self.archive or indexing:
      self.indexing = True
      self.index_init()
    self.caching = caching
    self.cache = []
    self.sort_key_separator = separator

  def error(self, exc, mail):
    """ Handle errors. """
    msg = "unkown error: " + str(exc[1]) 
    if exc[0] is sqlite3.IntegrityError:
      msg = 'can not add mail with Message-ID:"' + mail["Message-ID"]+ '" twice to result index'
    #traceback.print_tb(exc[2])
    sys.stderr.write(msg + "\n")

  def filter_mbox(self, obj):
    """ Filter a mailbox instance. """
    if isinstance(obj, str):
      obj = mailbox.mbox(obj)
    for mail in obj:
      self.filter_mail(mail)
    if isinstance(obj, mailbox.mbox):
      obj.close()

  def filter_mail(self, mail):
    """ Filter a single mail. """
    try:
      self.filtered += 1
      if (self.filter_mail_pass(mail)):
        if self.indexing: # and not caching # disables indexing
          self.index_add(mail)
        self.resultset_add(mail)
        self.passed += 1
    except:
      self.error(sys.exc_info(), mail)

  def filter_mail_pass(self, mail):
    """ Apply all filter rules. """
    self.filter_matches = {}
    boolean = True
    for header, regexp in self.filters:
       inner_boolean = False
       for header_value in header_values(header, mail):
		  # True if any header part is true:  
         inner_boolean |= self.filter_item_pass(header, regexp, header_value)
        # True if all filter items are true:
       boolean &= inner_boolean
    return boolean
           
  def filter_item_pass(self, header, regexp, strg):
    """ Apply a filter rule. """
    if type(regexp) is not None and len(regexp) > 0:
      if re.search(regexp, strg):
        self.filter_matches_add(header, strg)
        return True
      return False
    return True

  def filter_matches_add(self, key, value):
    """ Keep match of filter items."""
    if key in self.filter_matches.keys():
      self.filter_matches[key].append(value)
    else:
      self.filter_matches[key]=[value]

  def resultset_add(self, mail):
    """ Append mail to a result set. """
    if self.sort_keys_generate(mail) > 0:
      for key in self.sort_keys:
        handle = open(os.path.normpath(self.output + "/" + key + ".mbox"), "a")
        self.resultset_switch(handle, mail)
    else:
      self.resultset_switch(sys.stdout, mail)

  def resultset_switch(self, handle, mail):
    """ Cache mail or write mail to a result set. """
    if self.caching:
      self.cache.append(mail)
    else:
      self.resultset_output(handle, mail)

  def resultset_output(self, handle, mail):
    """ Write mail to a result set. """
    #print str(mail) todo: use this version with broken From?!
    genr = email.generator.Generator(handle, True, 0)
    genr.flatten(mail, True)	  
 
  def sort_keys_generate(self, mail):
    """ Generate the sort keys (result sets) for mail. """
    self.sort_keys = []
    for key, form in self.selectors:
       # Sort by filter matches only (1:1):
      if key in self.filter_matches.keys():
        self.sort_keys_add(key, form, self.filter_matches[key])
      # Sort by all header parts (1:N):
      else:
        self.sort_keys_add(key, form, header_values(key, mail))
    return len(self.sort_keys)

  def sort_keys_add(self, key, form, values):
    """ Append key part to sort keys (generates n*m sort keys for n and m key parts)."""
    new_keys = []
    for value in values:
      key_value = header_value_formatted(key, form, value) 
      # revoke empty key parts:
      if len(key_value) > 0:
        # No keys existing:
        if len(self.sort_keys) == 0:
          new_keys.append(key_value)
        else:
          for sort_key in self.sort_keys:
            new_keys.append(sort_key + self.sort_key_separator + key_value)
      else:
       sys.stderr.write("[NOTE] empty key part\n")
    # Reset to extended set of sort keys:
    self.sort_keys = new_keys
    
  def index_init(self):
    """ Initialize the result index database. """
    self.db = sqlite3.connect(self.index_path())
    self.db.execute('CREATE TABLE IF NOT EXISTS Mails ("MD5-Value" TEXT PRIMARY KEY, "Message-ID" TEXT, "From" TEXT NOT NULL, "To" TEXT NOT NULL, "Cc" TEXT, "Bcc", TEXT, Date TEXT NOT NULL, "In-Reply-To" TEXT, Subject TEXT)');

  def index_add(self, mail):
    """ Add mail header to result index. """ 
    self.db.execute('INSERT INTO Mails ("MD5-Value", "Message-ID", "From", "To", "Cc", "Bcc", Date, "In-Reply-To", Subject) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (self.index_md5_value(mail), header_strip(mail['Message-ID']), header_decode(mail['From']), header_decode(mail['To']), header_decode(mail['CC']), header_decode(mail['BCC']), header_decode(mail['Date']), header_strip(mail['In-Reply-To']), header_decode(mail['Subject'])))
    self.db.commit()

  def index_md5_value(self, mail):
    """ Determine a MD5 value for mail. """
    return md5_value(str(mail["Message-ID"] or "") + str(mail["Date"] or "") + str(mail["From"] or "") + str(mail["To"] or ""))
    
  def index_path(self):
    """ Determine the to the result index. """
    return os.path.normpath(self.output + "/" + self.resultset_index)

def md5_value(strg):
  """ Returns the md5 value in hex-fromat of strg """
  md5 = hashlib.md5()
  md5.update(strg.encode("UTF-8"))
  return md5.hexdigest()
	
def header_decode(strg):
  """ Decode header field. """
  if type(strg) is str:
    decoded = []
    for field in email.header.decode_header(strg):
      decoded.append(python_decode(field[0], field[1] or EMAIL_ENCO))
    return "".join(decoded)
  return ""

def header_email(strg):
  """ Filter first email from string """
  return re.search('([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,4})', strg).group(1)

def header_strip(strg, strip='[<>"]'):
  """ Remove encloseing brackets"""
  return re.sub(strip, '', strg or '')

def header_values(header, mail):
  """ Split header into a list of items """
  if header not in mail.keys():
    sys.stderr.write("[NOTE] header: "+header+" not found\n")
  value = header_decode(mail[header])
  cheader = header.capitalize()
  if cheader == "Date":
    return [value]
  elif cheader in ["From", "Cc", "Bc", "To", "Sender", "Reply-to"]:
    return value.split(",")
  return [value]

def header_value_formatted(key, form, value=""):
  """ Return formatted header values. """
  ckey = key.capitalize()
  if ckey in ["From", "Cc", "Bcc", "To", "Sender", "Reply-to"]:
    return header_email(value)
  elif ckey == "Date":
    return dateutil.parser.parse(value).strftime(form or DATE_FORMAT)
  # shorten sort key to 20 chars:
  if len(value or "") > 0:
    return (value or "")[:12] + "." + md5_value(value or "") 
  return ""

def python_decode(strg, enc):
  """ Decode strings for python < 3. """
  try:
    return strg.decode(enc)
  except:
    return strg

def cli_protocol(val):   
  m = re.search("^([^,;$ ]+)(?:,(.*)|()$)", val)      
  if m:
    return (m.group(1), m.group(2) or "")
  raise "[Error] protocol error"
    
def cli_usage(excp=None):
  if excp[0] is getopt.GetoptError:
    sys.stderr.write("[ERROR] "+ str(excp[1]) + "\n\n")
  sys.stderr.write("mboxfilter v"+__version__+"\n")
  sys.stderr.write("""Usage:
  mboxfilter [--help] [--version] [--dir output] [--unique] [--archive]
  [--filter_from regexp] [--filter_to regexp] [--filter_date regexp]
  [--filter header,regexp] [--sort_from] [--sort_to] [--sort_date format]
  [--sort header,regexp] [--nostat]
  mbox ...\n""")
  sys.exit(1)
	
def cli():
  """ Invoke mboxfilter from cmd."""
  try:
    opts, args = getopt.getopt(sys.argv[1:], None, ["dir=", "unique", "archive", "sort_from", "filter_from=", "sort_date=", "filter_date=", "filter_to=", "sort_to", "filter=", "sort=", "help", "nostat", "version"])
    output = None
    selectors = []
    archive = False
    filters = []
    unique = False
    nostat = False
    for opt, val in opts:
      val = python_decode(val, sys.stdin.encoding)
      if opt == "--dir":
        output = val
      elif opt == "--archive":
       archive = True
      elif opt == "--unique":
       unique = True
      elif opt == "--help":
        cli_usage()
      elif opt == "--version":
        cli_usage()
      elif opt == "--filter_from":
        filters.append(("From", val))
      elif opt == "--filter_to":
        filters.append(("To", val))
      elif opt == "--filter_date":
        filters.append(("Date", val))
      elif opt == "--filter":
        filters.append(cli_protocol(val))
      elif opt == "--sort_from":
        selectors.append(("From", None))
      elif opt == "--sort_to":
        sort_keys.append(("To", None))
      elif opt == "--sort_date":
        selectors.append(("Date", val))
      elif opt == "--sort":
        selectors.append(cli_protocol(val))
      elif opt == "nostat":
        nostat = True
    filt = Filter(output=output, archive=archive, indexing=unique, filters=filters, selectors=selectors)
    for mbox in args:
      filt.filter_mbox(mbox)
    if not nostat:
      sys.stderr.write(str(filt.filtered) + " mails filtered, " + str(filt.passed) + " passed in " + str(filt.output) + "\n")
  except:
    cli_usage(sys.exc_info())