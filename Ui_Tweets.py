# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file Ui_Tweets.ui
# Created with: PyQt4 UI code generator 4.4.4
# WARNING! All changes made in this file will be lost!

import os
from PyQt4 import QtCore, QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Tweets.ui'))

class Ui_Tweets(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(Ui_Tweets, self).__init__(parent)
        
        # Set up the user interface.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see http://goo.gl/E7M7e3
        self.setupUi(self)
