import json
import logging

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from semantic_version import Version

from src.errorChecking import isPrerelease
from src.constant_vars import VERSION

class checkUpdate(QObject):
    '''
    Instancing this object will run a series of 
    functions to get the latest Myth Mod Manager version.

    `checkUpdate` will delete itself after it's finished.
    '''

    updateDetected = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()

        link = 'https://api.github.com/repos/Wolfmyths/Myth-Mod-Manager/releases'

        if not isPrerelease(VERSION):
            link += '/latest'
        
        network = QNetworkAccessManager(self)
        request = QNetworkRequest(QUrl(link))
        
        self.reply = network.get(request)
        self.reply.finished.connect(self.__reply_handler)
    
    def __reply_handler(self) -> None:
        reply: QNetworkReply = self.sender()

        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.__checkVersion()
        else:
            logging.error('Internet error in checkUpdate():\n%s', reply.error())
    
    def __checkVersion(self) -> None:
        reply: QNetworkReply = self.sender()

        try:
            data: dict = json.loads(reply.readAll().data().decode())
        except Exception as e:
            logging.error('An error occured trying to access a Github API reply in checkUpdate().__checkversion():\n%s', str(e))
            return

        if isPrerelease(VERSION):
            latestVersion = Version.coerce(data[0]['tag_name'])
        else:
            latestVersion = Version.coerce(data['tag_name'])
        
        logging.info('Latest Version: %s', latestVersion)

        if latestVersion > VERSION:
            self.updateDetected.emit(latestVersion, data['body'])

        self.deleteLater()
                
