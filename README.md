# PyGmailAttachmentReader

## What is this?

This is a Python3 script that will
* automatically log into a gmail account.
* look for unread messages with a specific label.
* look for attachments to those messages with a specific mime time
    * Mime types are matched by prefix so "image/" matches "image/jpeg" or
      "image/png" or ...
* download those attachments into a specified directory using the filename
  from the mail message.
    * Warning: Currently this will overwrite existing files with the same name.
* Mark the message unread or move the message to trash, or simply remove the label.

The program can either run as a one-shot, or it can be configured to check periodically
until a request is received from the console to quit.

## Wait a minute.  Doesn't this already exist.

There are other programs on GitHub and elsewhere that do roughly the same thing,
however they require that you store your password in plain (or easily decodable)
text on your computer, or that you enter your password every time you run the program

> WARNING: Storing your password in plain text his is a terrible idea.  Please don't do it.

Other programs also require that you enable IMAP access to your gmail account and
configure it to accept weak user authentication.

> WARNING: This is not such a good idea, either.  Please don't do it.

## How do I use it?

### Register your copy of this as an application with Google.

  Do this once!

[Google has a web site for this](https://console.developers.google.com/apis/dashboard)
or you can read more by searching for "Google OAuth2".

##### Huh? Isn't GmailAttachmentReader already registered as an application?

GmailAttachmentReader was developed as part of another application (which may eventually show up on GitHub)
and is using that application's identity.  Since you will not be running they parent application
you can't use its identity.  But it's easy to get your own.

### Configure

Make a working copy of example configuration file: exampleConfig.json
I suggest a naming convention of config<yourGmailName>.json

Customize the file to taste (see "commments" in the file itself.)

Note you should use the application name you registered with google as the
"application" in the configuration file.

### Log into your gmail account (use any old browser you want to.)

### Give your application permission to access your gmail account.

  Do this once for each computer on which you run your application.

Start GmailAttachmentReader using this command:

 $ python gmailattachmentreader.py config*GmailAccount*.json

If all goes well your browser will display a screen that says roughly:

> YourApplication wants permission to modify messages in YourGmailAccout
   [Allow] or [Deny]

Once you grant permission you will be able to read messages from this account
"forever" and modify those messages by changing the label or marking them read.

## Why Python3?

Because it is a better language than Python2 and it is mature enough now that I
am hoping people start using it for "everything."

## Thanks.

You're welcome.

## Oh yeah.  How about licensing?

Read license.txt.   Briefly use it at will.  Just give me credit if it works and
don't blame me if it breaks.  
