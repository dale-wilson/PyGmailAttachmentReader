#!/usr/bin/env python3
"""
Read attachments from gmail into a directory.
Searches for unread messages with a configured label in a GMail account.
Download any attachments with a configured mime type into a configured
directory.
Optionally marks the message unread, moves it to trash, or removes the label.
Can run periodically or as a one-shot.
"""

import httplib2
import os
import errno
import argparse
import json
import base64
import time
import threading
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

###########
# Utility/general purpose functions
def getConfig(config, key, default):
    """
    Get a value from a configuration dictionary returning a default value
    if the key is not found.
    """
    if key in config:
        return config[key]
    else:
        return default

def optionallyCreateDirectory(path):
    """
    Create any missing directories in path.
    Ignores "already exists" execption.
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

class GmailAttachmentReader:
    """
    Download attachments from gmail message.
    Usage:
       construct a GmailAttachReader
       call start()
       call wait() # optional.  Feel free to provide your own wait technique.
       call stop()
    """

    def __init__(self, config, args):
        """
        Construct an attachment reader given a configuration dictionary and
        parsed command line arguments.

        Config is a dictionary with these keys:
            application -- the application name used to create gmail credentials
            credential_file -- the credentials (secrets) file from gmail
            authentication_file -- a file in which to save the authentication token
            checkEverySeconds -- how often to check for new messages (0 means check
                                once and exit
            label -- look only at unread messages with this label.
            dispose -- message disposition after success:
                  read: means mark it read
                  trash: means move the message to trash
                  unlabel: means remove the label defined by "label"
            mimeType -- What type of attachments to download (i.e. "image/"
            downloadDirectory -- where should downloaded attachments be stored
            capture_base64 -- for debugging, write the base64 attachment to a
                file before decoding it.
            verbose -- true.  Write extra information to standard out.
        args: are arguments parsed with argparse.ArgumentParser.  They are passed
              to gmail authentication process.
        """
        self._applicationName = config["application"]
        self._credentialFile = config["credential_file"]
        self._tokenFile = config["authentication_file"]
        self._label = config["label"]
        self._dispose = getConfig(config, "dispose", "read")
        self._checkEverySeconds = getConfig(config, "checkEverySeconds", 3600)
        self._mimeType = getConfig(config, "mimeType", "image/")
        self._captureBase64 = getConfig(config, "capture_base64", False)
        self._verbose = getConfig(config, "verbose", False)

        self._downloadDirectory = os.path.expanduser(
            os.path.expandvars(config["downloadDirectory"]))
        optionallyCreateDirectory(self._downloadDirectory)
        print("Downloading {} attachments from messages labeled {} to: {}".format(
            self._mimeType, self._label, self._downloadDirectory))

        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        optionallyCreateDirectory(credential_dir)
        credentialPath = os.path.join(credential_dir, self._tokenFile )

        store = Storage(credentialPath)
        credentials = store.get()
        if not credentials or credentials.invalid:
            googleAuthSite = "https://www.googleapis.com/auth/gmail.modify"
            flow = client.flow_from_clientsecrets(self._credentialFile, googleAuthSite)
            flow.user_agent = self._applicationName
            credentials = tools.run_flow(flow, store, args)
            print('Storing credentials to ' + credentialPath)
            store.put(credentials)
        self._credentials = credentials

        self._worker = None
        self._service = None
        self._stopRequested = False

    def authorize(self):
        """
            If not already authenticated, then get an authentication token
            from a token file or get a new token from google.
        """
        if not self._service:
            http = self._credentials.authorize(httplib2.Http())
            self._service = discovery.build('gmail', 'v1', http=http)
        if self._service:
            return True
        return False

    def start(self):
        """
            Start reading emails.
            If checkEverySeconds == 0 this is a one-shot.
        """
        if self._checkEverySeconds > 0:
            self._worker = threading.Thread(target=self)
            self._worker.start()
        else:
            self.getAttachmentsFromMessages()

    def wait(self):
        """ Run until the user asks to quit."""
        while self._worker != None:
            q = input("'q' to quit; n to check now")
            if q == 'q':
                break
            elif q == 'n':
                # TODO: consier concurrency
                self.getAttachmentsFromMessages(
                    label = self._label,
                    dispose = self._dispose)
            else:
                print("[{}]?\n".format(q))

    def __call__(self):
        """ The function called by the worker thread """
        print("Running")
        while not self._stopRequested:
            print("\n Checking every {} seconds".format(self._checkEverySeconds))
            self.getAttachmentsFromMessages(
                label = self._label,
                dispose = self._dispose)
            print("\n'q' to quit")
            for x in range(self._checkEverySeconds):
                time.sleep(1)
                if(self._stopRequested):
                    break
        print("Stopping")

    def stop(self):
        """ Ask the worker (if any) to stop, and wait for it to exit. """
        self._stopRequested = True
        if self._worker != None:
            self._worker.join()

    def listLabels(self):
        """
        List the labels defined for a mailbox.

        Diagnostic to be sure we can interact with the mail box.
        """
        if not self.authorize():
            return
        results = self._service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        if not labels:
            print('No labels found.')
        else:
            print('Labels:')
            for label in labels:
                print(label['name'])

    def getAttachmentsFromMessages(self, label="pipan", dispose="read"):
        """
        Find all messages with the given lable.
        Download attachments.
        Dispose of the message.
        """
        if not self.authorize():
            return
        labelIds = ['UNREAD']
        query = "label: " + self._label

        response = self._service.users().messages().list(
            userId="me", labelIds = labelIds, q=query).execute()
        if "messages" in response:
            messageList = response["messages"]
            for messageInfo in messageList:
              try:
                self._processMessageInfo(messageInfo, dispose)
              except Exception as ex:
                print("Ignoring exception {}".format(ex))

        else:
            print("\nNo new messages")

    def _processMessageInfo(self, info, dispose):
        """ Process one entry from the list messages query """
        messageId = info["id"]

        print("Retreving message",messageId)
        message = self._service.users().messages().get(userId="me", id=messageId
            ).execute()

        if self._verbose:
            print("Message keys: ", message.keys())

        payload = message["payload"]
        foundAttachment = False
        if "mimeType" in payload:
            if self._processAttachmentPart(messageId, payload):
                foundAttachment = True

        # for multi-part messages process each individual part.
        if "parts" in payload:
            parts = payload["parts"]
            if self._verbose:
                print("Message parts: ", parts.keys())

            for part in parts:
                if self._processAttachmentPart(messageId, part):
                    foundAttachment = True

        if foundAttachment:
            if dispose == "trash":
                self._trashMessage(messageId)
            elif dispose == "read":
                self._markMessageRead(messageId)
            elif dispose == "unlabel":
                self._removeMessageLabel(messageId, self._label)
            else:
                print("Mesage left in mailbox unchanged.")
        else:
            print("No attachments found in this message.")
            self._markMessageRead(messageId)

    def _processAttachmentPart(self, messageId, part):
        """
        Process one part of a multi-part messages or the
        only part of a single-part message
        """
        mimeType = part["mimeType"]
        if self._verbose:
            print ("MimeType:", mimeType)
        if mimeType.startswith(self._mimeType):
            filename = part["filename"]
            body = part["body"]
            if "attachmentId" in body:
              self._retrieveAttachment(messageId, filename, body["attachmentId"])
            elif "data" in body:
              self._processAttachment(filename, body)
            return True
        if self._verbose:
            print("Ignoring mime type:", mimeType)
        return False

    def _retrieveAttachment(self, messageId, filename, attachmentId):
        print("Retrieving {}".format(filename))
        attachment = self._service.users().messages().attachments().get(
            userId = "me",
            messageId=messageId,
            id=attachmentId ).execute()
        self._processAttachment(filename, attachment)

    def _processAttachment(self, filename, attachment):
        if self._verbose:
            print("base64 decoding attachment", filename, attachment.keys())
        b64Data = attachment['data']
        if self._captureBase64:
            captureName = filename + ".base64"
            print("Capture to", captureName)
            with open(captureName, "w") as captureFile:
                captureFile.write(b64Data)

        data = base64.urlsafe_b64decode(b64Data)
        filePath = os.path.join(self._downloadDirectory, filename)
        print("Writing attachment to", filePath)
        with open(filePath, "wb") as attachFile:
            attachFile.write(data)
        print("write complete")

    def _trashMessage(self, messageId):
        print("Message moved to trash")
        self._service.users().messages().trash(userId="me", id=messageId).execute()

    def _markMessageRead(self, messageId):
        print("Message marked read")
        body = {'removeLabelIds': ['UNREAD'], 'addLabelIds': []}

        self._service.users().messages().modify(userId="me", id=messageId, body=body).execute()

    def _removeMessageLabel(self, messageId, label):
        print("Removing", label, "message.")
        body = {'removeLabvelIds': [label], 'addLabelIds': []}
        self._service.users().messages().modify(userId="me", id=messageId, body=body).execute()

def main():
    parser = argparse.ArgumentParser(parents=[tools.argparser],
        description="Read Attachments from Gmail",
        epilog="See exampleConfig.json for configuration information.")
    parser.add_argument("configfile",
        nargs="?",
        default = "configGmailAccount.json",
        type=argparse.FileType("r"),
        help="The configuration file")
    args = parser.parse_args()
    config = json.load(args.configfile)
    app = GmailAttachmentReader(config, args)
    app.start()
    app.wait()
    app.stop()

if __name__ == "__main__":
    main()
