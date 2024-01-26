from __future__ import annotations
from typing import TYPE_CHECKING

import logging

import PySide6.QtGui as qtg
import PySide6.QtWidgets as qtw
from PySide6.QtCore import QThread

from src.widgets.QDialog.QDialog import Dialog

if TYPE_CHECKING:
    from src.threaded.workerQObject import Worker

class ProgressWidget(Dialog):
    '''
    QDialog object to show the progress of threaded functions
    '''

    def __init__(self, mode: Worker) -> None:
        super().__init__()
        logging.getLogger(__name__)

        self.setWindowTitle('Myth Mod Manager Task')

        self.mode = mode

        layout = qtw.QVBoxLayout()

        # Create QThread
        self.qthread = QThread()
        self.qthread.started.connect(self.mode.start)

        # Move task to QThread
        self.mode.moveToThread(self.qthread)

        # Label
        self.infoLabel = qtw.QLabel(self)

        # Progress bar and connecting signals
        self.progressBar = qtw.QProgressBar()
        self.mode.setTotalProgress.connect(lambda x: self.progressBar.setMaximum(x))
        self.mode.setCurrentProgress.connect(lambda x, y: self.updateProgressBar(x, y))
        self.mode.addTotalProgress.connect(lambda x: self.progressBar.setMaximum(self.progressBar.maximum() + x))
        self.mode.doneCanceling.connect(self.reject)
        self.mode.error.connect(lambda x: self.errorRaised(x))
        self.mode.succeeded.connect(self.succeeded)

        # Button
        buttons = qtw.QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = qtw.QDialogButtonBox(buttons)
        self.buttonBox.rejected.connect(self.cancel)

        for widget in (self.infoLabel, self.progressBar, self.buttonBox):
            layout.addWidget(widget)
        
        self.setLayout(layout)
    
    def exec(self) -> int:

        self.qthread.start()
        return super().exec()
    
    def errorRaised(self, message: str):
        logging.error(message)

        self.infoLabel.setText(f'{message}\nExit to continue')
        self.qthread.exit(1)

    def succeeded(self):
        self.progressBar.setValue(self.progressBar.maximum())
        self.infoLabel.setText('Done!')

        self.qthread.exit(0)

        self.accept()
    
    def closeEvent(self, arg__1: qtg.QCloseEvent) -> None:

        if self.qthread.isRunning():
            self.cancel()
        else:
            self.mode.deleteLater()
            self.qthread.deleteLater()
            return super().closeEvent(arg__1)
    
    def cancel(self):
        '''
        Sets the cancel flag to true in which FileMover() will exit the function
        after it's done a step and pass the success signal
        '''

        isModeCanceled = self.mode.cancel

        if isModeCanceled:
            self.qthread.exit(2)
            self.reject()

        logging.info('Task %s was canceled', str(self.mode))
        self.infoLabel.setText('Canceled, exit to continue')

        self.mode.cancel = True
    
    def updateProgressBar(self, x, y):

        newValue = x + self.progressBar.value()

        self.infoLabel.setText(y)
        self.progressBar.setValue(newValue)
