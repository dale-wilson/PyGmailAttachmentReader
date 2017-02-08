# PyGmailAttachmentReader

## What is this?

This is a Python3 script that will
* Automatically log into a GMail account.
* Look for unread messages with a specific label.
* Look for attachments to those messages with a specific mime type.
    * Mime types are matched by prefix so "image/" matches "image/jpeg" or
      "image/png" or ...
* Download those attachments into a specified directory using the filename
  from the mail message.
    * If no file name is specified in the mail message, make one up using a format
    you supply.
    * If a file already exists with the specified name, decorate the file name with 
    a generation number: i.e. (file.txt, file(1).txt, file(2).txt, etc.
* Mark the message *read*, or move the message to trash, or simply remove the label.

The program can either run as a one-shot, or it can be configured to check periodically
until a request is received from the console to quit.

## Wait a minute.  Doesn't this already exist?

There are other programs on GitHub and elsewhere that do roughly the same thing,
however they require that you store your password in plain (or easily decodable)
text on your computer, or that you enter your password every time you run the program

> WARNING: Storing your password in plain text is is a terrible idea.  Please don't do it.

Those other programs also require that you enable IMAP access to your account and
configure it to accept weak user authentication.

> WARNING: This is not such a good idea, either.  Please don't do it.

## How do I use it?

### Register your copy of this as an application with Google.

| Do this once!

[Google has a web site for this](https://console.developers.google.com/apis/dashboard)
or you can read more by searching for "Google OAuth2".

When you register your application you will receive a "secrets" file.  Store it
in a safe place.  Note that this is not as dangerous as storing a password.  If
someone gets a copy of your secrets file they can claim to be your application
which counts against the limit Google keeps of how often you can run your application
before you have to pay.  They will *not* have access to your private information.

#### Huh? Isn't GmailAttachmentReader already registered as an application?

GmailAttachmentReader was developed as part of another application (which may eventually show up on GitHub)
It runs using that application's identity.  Since you will not be running the parent application
you can't use its identity.  You will have to get your own, but it's easy and free.

### Configure

Make a working copy of example configuration file: exampleConfig.json
I suggest a naming convention of config*YourGmailName*.json

Customize the file to taste (see "commments" in the file itself.)

Note you should use the application name you registered with google as the
"application" in the configuration file.

Set credential_file to the path to the secrets file you got when
you registered your application

### Log into your GMail account (use any old browser you want to.)
Create a filter that will recognize the messages from which you want to
capture attachments and apply a label to them (the label you specified
in the config file.)

| I tell people to send pictures to *mygmailaccount*+photo@gmail.com.  GMail
ignores the field after the plus sign(+) and sends the message to my account
anyway but the filters can see the +photo so they know which messages I'm
interested in.   

### Give your application permission to access your GMail account.

| Do this once for each computer on which you run your application.

Start GmailAttachmentReader using this command:

 $ python gmailattachmentreader.py config*GmailAccount*.json

If all goes well your browser will display a screen that says roughly:

> YourApplication wants permission to modify messages in YourGmailAccout
   [Allow] or [Deny]

Once you grant permission GmailAttachmentReader will be able to read messages from this account
"forever" and modify those messages by changing the label or marking them read.

## Can I have a Mulligan?

If you ever want to revoke GMail access permission, simply delete the file
~/.credentials/*authentication_file* where *authentication_file* is the
filename you specified when you edited the config file.

After doing this you will have to re-authorize (or deny authorization) the next
time you run GmailAttachmentReader.

## What if I have more than one GMail account I want to read from?

Make a new configuration file and use a different name for the authentication_file
(that's why I suggested the naming convention that includes your email account name.)
Start GmailAttachmentReader and when it can't find the authentication process, it
will ask permission again.  Use your other email account this time.   After that
you will be able to switch back and forth between accounts by changing the
name of the configuration file on the command line used to start GmailAttachmentReader.

If you want to read from both accounts at the same time, you'll have to start
two copies of GmailAttachmentReader.

## Why Python3?

Because it is a better language than Python2 which in turn is better (in my opinion) than
the other scripting languages available.  Python3 is mature enough now that I
am hoping people start using it for "everything."

## Thanks.

You're welcome.

## Oh yeah.  How about licensing?

Read license.txt.   Briefly use it at will.  Just give me credit if it works and
don't blame me if it breaks.  (Seems fair enough to me.  I thought of offering a
money-back guarantee -- less handling costs -- to anyone who diesn't like it.)

## Cool.  All this information and no advertising!

Almost forgot.  I developed this on my own time for fun, but my daytime job is working
for [Object Computing, Inc.](http://ociweb.com/)  We do
a lot of good work with open source, and some amazing custom projects, too.  Check us
out next time you need some software development expertise for hire.  
