"""
Filter and sort mails from mboxes for archiving and reporting
"""
import email
import email.generator
import getopt
import hashlib
import mailbox
import os
import re
import sqlite3
import sys
import time
#import traceback # todo remove

# Actual version:
__version__ = "0.1.6"

# Header fields containing email addresses:
HEADER_ADDRESS_FIELDS = ["From", "Cc", "Bc", "To", "Sender", "Reply-to"]

# Archive mboxes (default):
DEFAULT_ARCHIVE = False
# Cache results (default):
DEFAULT_CACHEING = False
# Path of index db (default):
DEFAULT_DB = "index.sqlite3"
# Remove attachments (default):
DEFAULT_REDUCE = False
# Email Encoding (default):
DEFAULT_ENCODING = "ISO-8859-15"
# Export attachments (default):
DEFAULT_EXPORT = False
# Log failed mails (default):
DEFAULT_FAILURES = None
# Format resu
DEFAULT_FORMAT = "%Y"
# Create result index (default):
DEFAULT_INDEX = False
# Write result sets to dir (default):
DEFAULT_OUTPUT = "."
# Maximum length of key part (default):
DEFAULT_MAXLEN = 32
# Don't display errors and statistics
DEFAULT_QUIET = False
# Separate key parts by char (default):
DEFAULT_SEPARATOR = "."

class FilterBaseException(Exception):
	mesg=""
	def __str__(self):
		return self.mesg

class FilterException(FilterBaseException):
	mesg = "%s"
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return self.mesg %self.value

class DirectoryNotExisting(FilterException):
	mesg = "direcotry not found: %s"

class HeaderMissed(FilterException):
	mesg = "header not found: %s"

class RegularExpressionError(FilterException):
	mesg = "regular expr. invalid: "

class EmailMissed(FilterBaseException):
	mesg = "email address not found"

class EmptyKeyPart(FilterBaseException):
	mesg = "key part is empty"

class CLIProtocollError(FilterBaseException):
	mesg = "syntax error, expect: Header,Regexp"

class Filter:
	# Number of deleted payloads:
	deleted = 0
	# List of indexes of payloads to be deleted:
	delete_marked = []
	# Number of exported payloads:
	exported = 0
	# Keep exported payloads
	exported_payloads = []
	# Failed while processing:
	failed = 0
	# Keep failed mails, when caching:
	failed_mails = []
	# Keep filter matches in List:
	filter_matches = []
	# Number of filtered mails:
	filtered = 0
	# Do indexing by default:
	indexing = False
	# Number of passed mails:
	passed = 0
	# Keep passed mails, when caching:
	passed_mails = []
	# Filname of index database:
	resultset_index = DEFAULT_DB
	# Reference passed mails by key:
	resultset = {}
	# Do sorting by default:
	sort_date_default = DEFAULT_FORMAT
	# Keep sort keys in list:
	sort_keys = []  
	def __init__(self, output=DEFAULT_OUTPUT, archive=DEFAULT_ARCHIVE, indexing=DEFAULT_INDEX, filters=[], selectors=[], caching=DEFAULT_CACHEING, separator=DEFAULT_SEPARATOR, failures=DEFAULT_FAILURES, export_payload=DEFAULT_EXPORT, reduce_payload=DEFAULT_REDUCE, payload_exportpath=None, quiet=DEFAULT_QUIET):
		""" Initialize a Filter object.
			archive
				Archives emails. Same as indexing=True and selectors=[("Date", "Y")] (default False)

			caching
				Caches resultset. Disables output and indexing. (default False)
		
			export_payload
				Exports payloads with a filename attribute (default False)
				
			indexing
				Creates a index database called index.sqlite3. (default False)

			failure
				Appends failed mails to given file (default None)

			filters
				List of tuples, e.g. ("From", regexp), ("To", regexp) or ("Date", format)

			output
				Redirets output to the given directory (default ./)
	 
			payload_exportpath path
				Exports payloads into directory (default see output)

			reduce_payload
				Removes all payloads not of type text (default False)

			selectors
				List of tuples, e.g. ("From", None), ("To", None), ("Date", format). mails will be output to files.

			separator
				Separates key parts (default ".")

			quiet
				Supresses error messages
		"""
		# Output files to directory:ss
		self.output = output
		if self.output is None or not os.path.isdir(self.output):
			raise DirectoryNotExisting(self.output)
		# Archive mailbox:
		self.archive = archive
		# Filter mbox by list of filters:
		self.filters = filters
		# Sort mbox by list of selectors:
		self.selectors = selectors
		if self.archive and len(self.selectors) == 0:
			self.selectors.append(("Date", self.sort_date_default))
		if self.archive or indexing:
			self.indexing = True
			self.index_init()
		# Cache results - no output:
		self.caching = caching
		# TODO
		self.passed_mails = []
		# TODO
		self.passed = 0
		# Separate sort key items by:
		self.sort_key_separator = separator
		# Write failures to path:
		self.failure_path = failures
		# Delete payloads which are not text:
		self.reduce_payload = reduce_payload
		# Export payload which have a filename header field:
		self.export_payload = export_payload
		# Export payloads here:
		if payload_exportpath:
			self.payload_exportpath = payload_exportpath
		else:
			self.payload_exportpath = self.output
		# Display errors
		self.quiet = quiet

	def error(self, msg, mail):
		""" Output an error. """
		self.failed += 1
		if not self.quiet:
			sys.stderr.write("error: " + msg + "\n")
			try:
				self.error_pipe(mail)
			except:
				sys.stderr.write("error: can't log mail\n")

	def error_pipe(self, mail):
		""" Add mail to resultset of errors. """
		if self.caching:
			self.failed_mails.append(mail)
		elif self.failure_path:
			self.output_mail(open(os.path.normpath(self.failure_path), "a"), mail)
	
	def output_attachment(self, path, content):
		""" Write file to path. """
		with open(path, "w+b") as fd:
			fd.write(content)

	def output_mail(self, handle, mail):
		""" Write email to filehandle. """
		genr = email.generator.Generator(handle, True, 0)
		genr.flatten(mail, True)
		# Close mbox entry explicit:
		handle.write("\n")	  

			
	def filter_mbox(self, obj):
		""" Filter a mbox file or mailbox.mbox instance. """
		if isinstance(obj, str):
			if os.path.isfile(obj):
				obj = mailbox.mbox(obj)
		for mail in obj:
			self.filter_mail(mail)
		if isinstance(obj, mailbox.mbox):
			obj.close()

	def filter_mail(self, mail):
		""" Filter a single mail. """
		try:
			self.filtered += 1
			if self.filter_mail_pass(mail):
				if self.export_payload or self.reduce_payload:
					self.payload_parse(mail)
				if self.indexing: # and not caching # disables indexing
					self.index_add(mail)
				self.resultset_add(mail)
				self.passed += 1
		except sqlite3.IntegrityError as excp:
			self.error("can't add mail twice to result index", mail)
		except:
			#traceback.print_tb(sys.exc_info()[2])
			self.error(str(sys.exc_info()[1]), mail)

	def filter_mail_pass(self, mail):
		""" Apply all filters. """
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
		""" Apply filter. """
		try:
			if re.search(regexp, strg):#, flags=re.IGNORECASE):
				self.filter_matches_add(header, strg)
				return True
			return False
		except:
			raise RegularExpressionError(regexp)

	def filter_matches_add(self, key, value):
		""" Keep match of filter."""
		if key in self.filter_matches.keys():
			self.filter_matches[key].append(value)
		else:
			self.filter_matches[key]=[value]

	def payload_decode(self, payload):
		""" Decode the payload. """
		return payload.get_payload(decode=1)

	def payload_delete(self, mail):
		""" Remove makred payloads from mail. """
		offset = 0
		for idx in sorted(self.delete_marked):
			del mail.get_payload()[idx+offset]
			offset -= 1
			self.deleted += 1
		self.delete_marked = []

	def payload_export(self, payload, mail):
		""" Write payload to file. """
		fname = header_decode(payload.get_filename() or "")
		if fname:
			path = os.path.normpath("%s/%s" % (self.payload_exportpath, ".".join([email.utils.unquote(header_decode(mail["Message-ID"])), "%02d" %self.payload_index(payload, mail), fname])))
			self.output_attachment(path, self.payload_decode(payload))
			self.exported += 1

	def payload_handle(self, payload, mail):
		""" Handle payload by application logic and mime type. """
		if self.payload_is_handleable(payload):
			if self.export_payload:
				self.payload_pipe(payload, mail)
			if self.reduce_payload:
				# Mark email as deleted:
				self.delete_marked.append(self.payload_index(payload, mail))

	def payload_index(self, payload, mail):
		""" Return index of payload """
		return mail.get_payload().index(payload)

	def payload_parse(self, mail):
		""" Handle all payloads of the mail. """
		if mail.is_multipart():
			for payload in mail.get_payload():
				if payload.get_content_maintype() == "multipart":
					self.payload_parse(payload)
				else:
					self.payload_handle(payload, mail)
			# Post deletion of payloads:
			self.payload_delete(mail)

	def payload_is_handleable(self, payload):
		""" Select payload for processing by mime type. """
		if payload.get_filename():
			return True
		return False

	def payload_pipe(self, payload, mail):
		""" Pipe payload either to file or cache. """
		if self.caching:
			self.exported_payloads.append(self.payload_decode(payload))
		else:
			self.payload_export(payload, mail)

	def resultset_add(self, mail):
		""" Append mail to a result set. """
		if self.sort_keys_generate(mail) > 0:
			for key in self.sort_keys:
				self.resultset_pipe(key, mail)
		else:
			self.resultset_pipe(None, mail)

	def resultset_pipe(self, key, mail):
		""" Pipe mail either to file or cache. """
		if self.caching:
			self.resultset_cache(key, mail)
		else:
			self.resultset_output(key, mail)

	def resultset_cache(self, key, mail):
		""" Cache results """
		self.passed_mails.append(mail)
		if key in self.resultset:
			self.resultset[key].append(mail)
		else:
			self.resultset[key]=[mail]

	def resultset_output(self, key, mail):
		""" Write mail to a result set. """
		handle = sys.stdout
		if key is not None:
			handle = open(os.path.normpath(self.output + "/" + key + ".mbox"), "a")
		self.output_mail(handle, mail)

	def sort_keys_generate(self, mail):
		""" Determine the sort keys for a mail. """
		# Reset sort keys for every mail:
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
			key_value = header_format(key, value, form) 
			# revoke empty key parts:
			if len(key_value) > 0:
				# No keys existing:
				if len(self.sort_keys) == 0:
					new_keys.append(key_value)
				else:
					for sort_key in self.sort_keys:
						new_keys.append(sort_key + self.sort_key_separator + key_value)
			else:
				raise EmptyKeyPart()
		# Reset to extended set of sort keys:
		self.sort_keys = new_keys
	  
	def index_init(self):
		""" Initialize the result index database. """
		self.db = sqlite3.connect(self.index_path())
		self.db.execute('CREATE TABLE IF NOT EXISTS Mails ("MD5-Value" TEXT PRIMARY KEY, "Message-ID" TEXT, "From" TEXT NOT NULL, "To" TEXT NOT NULL, "Cc" TEXT, "Bcc", TEXT, Date TEXT NOT NULL, "In-Reply-To" TEXT, Subject TEXT)');

	def index_add(self, mail):
		""" Add mail header to result index. """
		self.db.execute('INSERT INTO Mails ("MD5-Value", "Message-ID", "From", "To", "Cc", "Bcc", Date, "In-Reply-To", Subject) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (self.index_md5_value(mail), email.utils.unquote(header_decode(mail['Message-ID'])), header_decode(mail['From']), header_decode(mail['To']), header_decode(mail['CC']), header_decode(mail['BCC']), header_decode(mail['Date']), email.utils.unquote(header_decode(mail['In-Reply-To'])), header_decode(mail['Subject'])))
		self.db.commit()

	def index_md5_value(self, mail):
		""" Determine a MD5 value for mail. """
		return md5_value(header_decode(mail["Message-ID"]) + header_decode(mail["Date"]) + header_decode(mail["From"]) + header_decode(mail["To"]))
	  
	def index_path(self):
		""" Determine the to the result index. """
		return os.path.normpath(self.output + "/" + self.resultset_index)

def md5_value(strg):
	""" Returns the md5 value in hex-fromat of strg """
	md5 = hashlib.md5()
	md5.update(strg.encode('UTF-8'))
	return md5.hexdigest()
	
def header_decode(strg):
	""" Decode header field. """
	decoded = []
	for field in email.header.decode_header(strg or ""):
		decoded.append(python_decode(field[0], field[1] or DEFAULT_ENCODING))
	return "".join(decoded)

def header_email(strg):
	""" Grep email from header value """
	addr = email.utils.parseaddr(strg)
	if not addr[1]:
		raise EmailMissed(strg)
	return addr[1]
	  
def header_values(header, mail):
	""" Split header into a list """
	if header not in mail.keys():
		raise HeaderMissed(header)
	values = [header_decode(mail[header])]
	if header in HEADER_ADDRESS_FIELDS:
		return [email.utils.formataddr(x) for x in email.utils.getaddresses(values)]
	return values

def header_format(header, value, form = DEFAULT_FORMAT):
	""" Format header value by type. """
	if header in HEADER_ADDRESS_FIELDS:
		return header_email(value)
	elif header == "Date":
		parsed = email.utils.parsedate(value)
		if parsed:
			return time.strftime(form, parsed)
		return ""
	if header == "Message-ID":
		return email.utils.unquote(value)
	return value[:DEFAULT_MAXLEN]

def python_decode(strg, enc):
	""" Decode strings for python < 3. """
	if type(strg) is bytes:
		return strg.decode(enc)
	return strg

def cli_protocol(val):   
	m = re.search("^([^,;$ ]+)(?:,(.*)|()$)", val)      
	if m:
		return (m.group(1), m.group(2) or "")
	raise CLIProtocollError()

def cli_info():
	sys.stderr.write("mboxfilter v"+__version__+"\n")

def cli_usage():
	sys.stderr.write("""Usage:
	mboxfilter [--help] [--version] [--dir output] [--unique] [--archive]
	[--filter_from regexp] [--filter_to regexp] [--filter_date regexp]
	[--filter header,regexp] [--sort_from] [--sort_to] [--sort_date format]
	[--sort header,regexp] [--failures path] [--quiet]
	[--export] [--exportpath path] [--reduce]
	mbox ...\n""")
	
def cli():
	""" Invoke mboxfilter from cmd."""
	try:
		opts, args = getopt.getopt(sys.argv[1:], None, ["dir=", "unique", "archive", "sort_from", "filter_from=", "sort_date=", "filter_date=", "filter_to=", "sort_to", "filter=", "sort=", "help", "quiet", "version", "failures=", "export", "exportpath=", "reduce"])
		output = DEFAULT_OUTPUT
		selectors = []
		archive = DEFAULT_ARCHIVE
		filters = []
		unique = False
		quiet = DEFAULT_QUIET
		failures = DEFAULT_FAILURES
		export = DEFAULT_EXPORT
		exportpath = None
		reduce = DEFAULT_REDUCE
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
				sys.exit(0)
			elif opt == "--version":
				cli_info()
				sys.exit(0)
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
				selectors.append(("To", None))
			elif opt == "--sort_date":
				selectors.append(("Date", val))
			elif opt == "--sort":
				selectors.append(cli_protocol(val))
			elif opt == "--quiet":
				quiet = True
			elif opt == "--failures":
				failures = val
			elif opt == "--export":
				export = True
			elif opt == "--exportpath":
				exportpath = val
			elif opt == "--reduce":
				reduce = True
		filt = Filter(output=output, archive=archive, indexing=unique, filters=filters, selectors=selectors, failures=failures, export_payload=export, payload_exportpath=exportpath, reduce_payload=reduce, quiet=quiet)
		for mbox in args:
			filt.filter_mbox(mbox)
		if not quiet:
			sys.stderr.write("%s filtered, %s passed, %s failed, %s exported, %s deleted\n" %(str(filt.filtered), str(filt.passed), str(filt.failed), str(filt.exported), str(filt.deleted)))
	except getopt.GetoptError as excp:
		sys.stderr.write(str(excp)+"\n\n")
		cli_usage()
		sys.exit(1)
	except DirectoryNotExisting as excp:
		sys.stderr.write(str(excp))
		sys.exit(1)
	except SystemExit:
		pass
	except:
		traceback.print_tb(sys.exc_info()[2])
		sys.stderr.write(str(sys.exc_info()[1]));
		sys.exit(1)