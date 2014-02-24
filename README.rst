==========
mboxfilter
==========

`mboxfilter <http://pamoller.com/mboxfilter.html>`_ is a Python class for filtering and sorting mailboxes (mbox-format) by `header fields <http://tools.ietf.org/html/rfc5322#section-3.6>`_. The mailboxes can also be decomposed by removing and exporting attachments. You may find mboxfilter useful for archiving and reporting. mboxfilter can be invoked by a command line tool also called mboxfilter, which comes with the package. It acts as wrapper around the class. In the following example mboxfilter greps all emails sent from Peter to Frank:

::

    $ mboxfilter --filter_from "peter@(?:work.com|home.org)" --filter_to "frank@" peter2012.mbox peter2013.mbox

All filters accept regular expressions. They are matched against the values of the corresponding header fields. In the example above the regular expression peter@(?:work.com|home.org) is matched against From and frank@ against To of every email stored in the mbox files peter2012.mbox and peter2013.mobx. An email is added to the result set if every regular expression match. The result set will be printed to STDOUT by default. In addition mboxfilter is able to sort the result set before output like in the following example. All emails sent from Peter are sorted by the receiver's email address and the year of submission.

::

    $ mboxfilter --filter_from "peter@home.org" --sort_to --sort_date %Y peter2012.mbox peter2013.mbox
    $ ls
    frank@home.org.2012.mbox
    frank@home.org.2013.mbox
    rosie@home.org.2012.mbox

A sort operation produces different result sets and mboxfilter writes every result set to a own file. One email may be a member of several result sets. In the example above an email written to Frank and Rosie occurs in: rosie@home.org.2012.mbox and frank@home.org.2012.mbox. The sort operations reject options, except the date sort. It expects a `format string <http://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior>`_. In the follwoing exmple mboxfilter archives mailboxes of Peter:

::

    $ mboxfilter --archive peter@home.org.mbox peter@work.com.mbox
    $ ls 
    2012.mbox
    2013.mbox
    index.sqlite3

While archiving mboxfilter forms an index entry by important header values of each email and saves it in the index database index.sqlite3. The index avoids a second addition of an archived email. But the index databsae can be queried by SQLite 3. mboxfilter can also decompose mailboxes by removing and exporting attachments like in the following example:

::

    $ mboxiflter --export --reduce peter@home.org
    $ ls
    mxsdiykg.01.holiday.jpg
    mxsdiykg.02.report.pdf

More complex tasks can be done by using the Python class. In the following example mboxfilter greps all emails sent from Peter to Rosie whatever which header field (To, Cc or Bcc) was used to define Rosie as the receiver. The parameter caching=True causes mboxilter in line 6 to store the result set in the class member passed_mails instead of writing them it to STDOUT.

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

    class mboxfilter.Filter(output ::= "./", archive ::= False, indexing ::= False, filters ::= [], selectors ::= [], caching ::= False, separator ::= ".", failures ::= None, export_payload ::= False, reduce_payload ::= False, payload_exportpath ::= ".", quiet ::= False)

The Filter class can be used to instantiate own filters. The parameter filters takes a list of tuples, e.g.: [("From", "peter@home.org"), ("To", "rosie@home.org")]. The first item of the tuple references a name of a header field. It's value is matched against the regular expression within the second item. (The matches are kept, see below). An email is added to the result set if every filter match.

The parameter selectors takes also a list of tuples. The first item of the tuple registers a header field for sorting the filtered result set. The second item of the tuple is ignored, except for the header field Date. It expects a `format string <http://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior>`_ to extract a approbative date string from the value of the header field. A list of selectors may look like: [("To", None), ("Date", "%Y")]. mboxiflter uses the selectors to create a set of key parts for every email within the filtered result set. The key parts are used to form a sort key. Therefore the key parts are concatenated by the value of parameter separator. The header fields From, To, Cc and Bcc may produce multiple sort keys for a single email, because an email sent to many receivers has to be member of the result set of every receiver. But if a header field acts as filter and selector mboxfilter forms result sets only for matching email-addresses. E.g. the expression  filters=[('To', 'rosie@home.org')], selectors=[('To', None)] produces only a result set for Rosie.

In the absence of any selector mboxfilter prints the result set to STDOUT. Otherwise the sort keys are used as file names. The paramter failures redirect all failed emails to the given path. The parameter output redirects all files to the given directory. The parameter indexing=True causes mboxfilter to form a uniq result set. Therefore it creates the result set database index.sqlite3. The Parameter archive=True is a shorthand for indexing=True, selectors=[("Date", "%Y")]. The parameter caching=True redirects the result set to the class members passed_mails, failed_mails and resultset. The sort keys act as keys of the dictionary resultset.

The parameter export_payload exports all attachment from a multipart email to a file. payload_exportpath redirects the attachment to the given directory. reduce_payload removes the attachment from the email. Every message within an multipart email having a filename attribute is treated as attachment. The setting quiet=True supresses the output of error messages.

=======
Members
=======

::

    filtered ::= 0

Number of emails that have been processed.

::

    passed ::= 0

Number of emails that have been added to any result set.

::

    failed ::= 0

Number of emails that have failed.

::

    passed_mails ::= []

Result set, if parameter caching was set.

::

    failed_mails ::= []

List of Failed, if parameter caching was set.

::

    resultset ::= {}

Result set. The sort keys acts as keys of the dictionary.

=======
Methods
=======

::

     filter_mbox(obj)

filter_mbox process every email of the mailbox refrenced by obj. Obj can be either an instance of the mailbox.mbox class or a path referring to a mailbox in mbox format.

::

     filter_mail(mail)

filter_mail process a given instance of the mailbox.mboxMessage class.

===
Cmd
===

::

    mboxfilter [--help] [--version] [--quiet] [--dir path] [--failures path] [--unique] [--archive] [--filter_from regexp] [--filter_to regexp] [--filter_date regexp] [--filter header,regexp] [--sort_from] [--sort_to] [--sort_date format] [--sort header,regexp] [--reduce] [--export] [--exportpath path] mbox ...