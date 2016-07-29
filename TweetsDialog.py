# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name			 	 : Search Geo Tweets
Description          : This is work and extended analog of geotweet
Date                 : 09/Jul/16
copyright            : (C) 2016 by Maksym Vlasov
email                : m.vlasov@post.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4 import QtGui, uic
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Ui_Tweets.ui'))


# create the dialog for Tweets
class TweetsDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(TweetsDialog, self).__init__(parent)
        self.setupUi(self)
