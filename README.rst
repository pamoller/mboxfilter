==========
mboxfilter
==========

`mboxfilter <http://pamoller.com/mboxfilter.html>`_ is a Python class for filtering and sorting emails in mailboxes (mbox-format) by values of `header fields <http://tools.ietf.org/html/rfc5322#section-3.6>`_. You may find it useful for archiving and reporting. Basic filtering an sorting can be done by the command line tool mboxfilter, which comes with mboxfilter and acts as wrapper around the class. All emails send from Peter to Frank are grepped from a bunch of mailboxes easyly:

::

    $ mboxfilter --filter_from "peter@(?:work.com|home.org)" --filter_to frank@work.com peter2012.mbox peter2013.mbox

All filters accept regular expressions. In the example above they are matched to the values of the header fields From and To. An email passes a filter if every filter item is passed. The output is printed to stdout by default. To sort all emails sent from Peter by reciver and year is done by:

::

    $ mboxfilter --filter_from "peter@home.org" --sort_to --sort_date %Y peter2012.mbox peter2013.mbox
    $ ls
    frank@home.org.2012.mbox
    frank@home.org.2013.mbox
    rosie@home.org.2012.mbox ...

Sorting may produces different result set. Each result set is written to a own file. Note: An email wirtten to Frank and Rosie is added to two result sets - as shown above. Sorting by Date accepts a `format string <http://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior>`_ as argument. mboxfilter can also be used for archiving emails. All emails of Peter are archived by:

::

    $ mboxfilter --archive peter@home.org.mbox peter@work.com.mbox
    $ ls 
    2012.mbox
    2013.mbox
    index.sqlite3

Important header values of the emails are bundeled in a row and added to the index database index.sqlite3. The index revokes emails from being added twice. But the SQLite 3 database is also meant for querying by SQL.

More complex tasks can be done by using the Python class. For finding all emails sent from Peter to Rosie (To, Cc or Bcc) is done by:

::

    #!/usr/bin/env python
    from mboxfilter import Filter
    import sys
    passed = []
    for header in ["To", "Cc", "Bcc"]:
      f = Filter(caching=True, filters=[("From", sys.argv[0]), (header, sys.argv[1])])
      f.filter(sys.argv[2])
      passed = passed + f.passed_mails
    res = Filter(selectors=[("Date", "%Y")])
    res.filter(passed) 

=====
Class
=====

::

    class mboxfilter.Filter(output ::= "./", archive ::= False, indexing ::= False, filters ::= [], selectors ::= [], caching ::= False, separator ::= ".", failures ::= None)

The Filter class can be used to instantiate own filters. The parameter filters takes a list of tuples, e.g.: [("From", "peter@home.org"), ("To", "rosie@home.org")]. The first item of the tuple references the name of a header field. It's value is matched against the regular expression within the second item. (The matches are kept, see below) An email passes a  filter if every filter item is passed (matched). That are all emails from Peter to Rosie in the preceding example.


The tuples, which are listed in the parameter selectors, sort the emails into different result sets. The selector tuples are structured like the filter tuples, but without a regular expressions. The second value is ignored, except for the Date filed. The Date field expects a `format string <http://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior>`_ to extract a approbative date string from the Date field. A list of selectors may look like: [("To", None), ("Date", "%Y")]. The selectors constructs for every email a set of sort keys. A sort key is a string, which consists of a sequence of key parts separated by the value of parameter separator. A key part is made from the header's value by the following rules. a)  From, To, Cc, Bcc: a list of email-addresses, b) Date: a user formatted representation of the date and c)  any other: the first 12 chars and the md5 value of the header value. Possible sort keys for the example above are: rosie@home.org.2012 and rosie@home.org.2013.

Note: Header fields like From, To, Cc or Bcc may create more than one sort key per email, e.g. emails sent to two recivers with filters=[] and selector=[("To", None)]: The list of recivers forms two result sets: rosie@home.org and frank@work.com.

Note: If a header field was used as filter before, e.g. filters=[('To', 'rosie@home.org')] and selectors=[('To', None)], the matches will be used to from the sort key instead of the list of recivers: rosie@home.org only.

Without any selector the filtered emails are printed to stdout. Otherwise the sort keys are used as file names. The parameter output can be used to write the files into an existing directory. The parameter indexing=True creates the result set database in the file index.sqlite3. The Parameter archive=True is a shorthand for the parameter combination: indexing=True and selectors=[("Date", "%Y")]. It is useful for adding mails once in an archive. The parameter caching=True redirects the output to the class members passed_mails and failed_mails. This setting disables  indexing and ignores any selector.

If an error ocurs while filtering an email, e.g. the email obmits a header field, the email will appended to the file given in the failures parameter.

=======
Members
=======

::

    filtered ::= 0

Number of emails that have been filtered. 

::

    passed ::= 0

Number of emails, that have passed the filters. 

::

    failed ::= 0

Number of emails, that have failed while procession. 

::

    passed_mails ::= []

List of passed emails, if parameter caching was set.

::

    failed_mails ::= []

List of emails which failed, if parameter caching was set.

=======
Methods
=======

::

     filter_mbox(obj)

filter_mbox apply all filters and selectors to every email in the referenced mailbox. The Parameter obj can be either an instance of the mailbox.mbox class or a path referring to a mailbox within the mbox format.

::

     filter_mail(mail)

filter_mail apply all filters and selectors to the parameter mail, an instance of the mailbox.mboxMessage class.

===
Cmd
===

::

    mboxfilter [--help] [--version] [--nostat] [--dir output] [--failures path] [--unique] [--archive] [--filter_from regexp] [--filter_to regexp] [--filter_date regexp] [--filter header,regexp] [--sort_from] [--sort_to] [--sort_date format] [--sort header,regexp] mbox ...

For simple tasks the wrapper mboxfilter can be used as shown in the beginning. To use any header field for filtering or for sorting the options filter or sort are used. Note: the name of the header field and the regexp (Regular Expression) are separated by a ",". The option nostat suppresses the printing of a statistic to stderr.