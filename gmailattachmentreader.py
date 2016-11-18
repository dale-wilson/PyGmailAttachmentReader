"""
Read attachments from email into a directory
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
    Use:
       construct a GmailAttachReader
       call start()
       call wait() # optional.  Feel free to provide your own wait technique.
       call stop()
    """

    def __init__(self, config, args):
        """
        Construct an attachment reader given a configuration dictionary and
        parsed command line arguments.

        Dictionary:
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

        args: are passed to gmail authentication process.

        """
        self.__applicationName = config["application"]
        self.__credentialFile = config["credential_file"]
        self.__tokenFile = config["authentication_file"]
        self.__label = config["label"]
        self.__dispose = getConfig(config, "dispose", "read")
        self.__checkEverySeconds = getConfig(config, "checkEverySeconds", 3600)
        self.__mimeType = getConfig(config, "mimeType", "image/")
        self.__captureBase64 = getConfig(config, "capture_base64", False)
        self.__verbose = getConfig(config, "verbose", False)

        self.__downloadDirectory = os.path.expanduser(
            os.path.expandvars(config["downloadDirectory"]))
        optionallyCreateDirectory(self.__downloadDirectory)
        print("Downloading {} attachments to: {}".format(
            self.__mimeType, self.__downloadDirectory))

        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        optionallyCreateDirectory(credential_dir)
        credentialPath = os.path.join(credential_dir, self.__tokenFile )

        store = Storage(credentialPath)
        credentials = store.get()
        if not credentials or credentials.invalid:
            googleAuthSite = "https://www.googleapis.com/auth/gmail.modify"
            flow = client.flow_from_clientsecrets(self.__credentialFile, googleAuthSite)
            flow.user_agent = self.__applicationName
            credentials = tools.run_flow(flow, store, args)
            print('Storing credentials to ' + credentialPath)
            store.put(credentials)
        self.__credentials = credentials

        self.__worker = None
        self.__service = None
        self.__stopRequested = False

    def authorize(self):
        if not self.__service:
            http = self.__credentials.authorize(httplib2.Http())
            self.__service = discovery.build('gmail', 'v1', http=http)
        if self.__service:
            return True
        return False

    def start(self):
        if self.__checkEverySeconds > 0:
            self.__worker = threading.Thread(target=self)
            self.__worker.start()
        else:
            self.getAttachmentsFromMessages()

    def wait(self):
        while self.__worker != None:
            q = input("'q' to quit; n to check now")
            if q == 'q':
                break
            elif q == 'n':
                # TODO: consier concurrency
                self.getAttachmentsFromMessages(
                    label = self.__label,
                    dispose = self.__dispose)

            else:
                print("[{}]?\n".format(q))

    def __call__(self):
        print("Running")
        while not self.__stopRequested:
            print("\n Checking every {} seconds".format(self.__checkEverySeconds))
            self.getAttachmentsFromMessages(
                label = self.__label,
                dispose = self.__dispose)
            print("\n'q' to quit")
            for x in range(self.__checkEverySeconds):
                time.sleep(1)
                if(self.__stopRequested):
                    break
        print("Stopping")

    def stop(self):
        self.__stopRequested = True
        if self.__worker != None:
            self.__worker.join()

    def listLabels(self):
        """
        List the labels defined for a mailbox.

        Diagnostic to be sure we can interact with the mail box.
        """
        if not self.authorize():
            return
        results = self.__service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        if not labels:
            print('No labels found.')
        else:
            print('Labels:')
            for label in labels:
                print(label['name'])

    def getAttachmentsFromMessages(self, label="pipan", dispose="read"):
        if not self.authorize():
            return
        labelIds = ['UNREAD']
        query = "label: " + self.__label

        response = self.__service.users().messages().list(
            userId="me", labelIds = labelIds, q=query).execute()
        if "messages" in response:
            messageList = response["messages"]
            for messageInfo in messageList:
              try:
                self.__processMessageInfo(messageInfo, dispose)
              except Exception as ex:
                print("Ignoring exception {}".format(ex))

        else:
            print("\nNo new messages")

    def __processMessageInfo(self, info, dispose):
        messageId = info["id"]

        print("Retreving message",messageId)
        message = self.__service.users().messages().get(userId="me", id=messageId
            ).execute()

        if self.__verbose:
            print("Message keys: ", message.keys())

        payload = message["payload"]
        foundAttachment = False
        if "mimeType" in payload:
            if self.__processAttachmentPart(messageId, payload):
                foundAttachment = True

        if "parts" in payload:
            parts = payload["parts"]
            if self.__verbose:
                print("Message parts: ", parts.keys())

            for part in parts:
                if self.__processAttachmentPart(messageId, part):
                    foundAttachment = True

        if foundAttachment:
            if dispose == "trash":
                self.__trashMessage(messageId)
            elif dispose == "read":
                self.__markMessageRead(messageId)
            elif dispose == "unlabel":
                self.__removeMessageLabel(messageId, self.__label)
            else:
                print("Mesage left in mailbox unchanged.")
        else:
            print("No attachments found in this message.")
            self.__markMessageRead(messageId)

    def __processAttachmentPart(self, messageId, part):
        mimeType = part["mimeType"]
        print ("MimeType:", mimeType)
        if mimeType.startswith(self.__mimeType):
            filename = part["filename"]
            body = part["body"]
            if "attachmentId" in body:
              self.__retrieveAttachment(messageId, filename, body["attachmentId"])
            elif "data" in body:
              self.__processAttachment(filename, body)
            return True
        print("Ignoring mime type:", mimeType)
        return False

    def __retrieveAttachment(self, messageId, filename, attachmentId):
        print("Retrieving {} from {}".format(filename, attachmentId))
        attachment = self.__service.users().messages().attachments().get(
            userId = "me",
            messageId=messageId,
            id=attachmentId ).execute()
        self.__processAttachment(filename, attachment)

    def __processAttachment(self, filename, attachment):
        print("base64 decoding attachment", filename, attachment.keys())
        b64Data = attachment['data']
        if self.__captureBase64:
            captureName = filename + ".base64"
            print("Capture to", captureName)
            with open(captureName, "w") as captureFile:
                captureFile.write(b64Data)

        data = base64.urlsafe_b64decode(b64Data)
        filePath = os.path.join(self.__downloadDirectory, filename)
        print("Writing attachment to", filePath)
        with open(filePath, "wb") as attachFile:
            attachFile.write(data)
        print("write complete")

    def __trashMessage(self, messageId):
        print("Message moved to trash")
        self.__service.users().messages().trash(userId="me", id=messageId).execute()

    def __markMessageRead(self, messageId):
        print("Message marked read")
        body = {'removeLabelIds': ['UNREAD'], 'addLabelIds': []}

        self.__service.users().messages().modify(userId="me", id=messageId, body=body).execute()

    def __removeMessageLabel(self, messageId, label):
        print("Removing", label, "message.")
        body = {'removeLabvelIds': [label], 'addLabelIds': []}
        self.__service.users().messages().modify(userId="me", id=messageId, body=body).execute()

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
    app()

if __name__ == "__main__":
    main()
