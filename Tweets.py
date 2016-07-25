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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4 import QtGui
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from TweetsDialog import TweetsDialog
import qgis.utils
import os.path

class Tweets: 

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
                which provides the hook by which you can manipulate the QGIS
                application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Tweets_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = TweetsDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Search GeoTweets')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Tweets')
        self.toolbar.setObjectName(u'Tweets')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """

        return QCoreApplication.translate('Tweets', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):    
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Tweets/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Run'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&Tweets'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # run method that performs all the real work
    def run(self): 
        # create and show the dialog 
        dlg = TweetsDialog() 
        self.dlg.show

        self.dlg.search_method.clear()
        self.dlg.output_metadata.clear()
        self.dlg.time_day.clear()
        self.dlg.time_hour.clear()
        self.dlg.time_minute.clear()
        
        self.dlg.search_method.addItem('Realtime (Streaming API)')
        self.dlg.search_method.addItem('In History (REST API)')

        self.dlg.output_metadata.addItem('Minimum (created_at, text, coordinates)')
        self.dlg.output_metadata.addItem('All (need more RAM / big files)')
        self.dlg.output_metadata.addItem('None - Only coordinates')

        result = self.dlg.exec_() 
        
        # See if OK was pressed
        if not result:
            return False 

        try:
            import json, shapefile, time
            from datetime import datetime
            from tweepy import Stream, OAuthHandler
            from tweepy.streaming import StreamListener
            from keys import keys

        except ImportError:
            raise Exception("Tweepy module not installed correctly")
        
        #Load new Twitter API keys
        CONSUMER_KEY = self.dlg.consumer_key.text()
        CONSUMER_SECRET = self.dlg.consumer_key_secret.text()
        ACCESS_TOKEN = self.dlg.access_token.text()
        ACCESS_TOKEN_SECRET = self.dlg.access_token_secret.text()

        #If have new Twitter API keys - Save
        if CONSUMER_KEY and CONSUMER_SECRET and \
           ACCESS_TOKEN and ACCESS_TOKEN_SECRET:
        
            open(self.plugin_dir + '/keys.py', 'w').write("keys = dict(\n\
                consumer_key = '" + CONSUMER_KEY + "',\n\
                consumer_secret = '" + CONSUMER_SECRET + "',\n\
                access_token = '" + ACCESS_TOKEN + "',\n\
                access_token_secret = '" + ACCESS_TOKEN_SECRET + "',\n)") 

        #If haven't new & previous Twitter API keys - Stop
        elif keys['consumer_key'] == '' or \
             keys['consumer_secret'] == '' or \
             keys['access_token'] == '' or \
             keys['access_token_secret'] == '':
                    
            warningMessage = qgis.utils.iface.messageBar().createMessage(\
                "No Twitter API keys! Please, enter them and try again")
            qgis.utils.iface.messageBar().pushWidget(\
                warningMessage, qgis.utils.iface.messageBar().WARNING)
            return False
        
        #Load previous Twitter API keys
        else: 
            CONSUMER_KEY = keys['consumer_key']
            CONSUMER_SECRET = keys['consumer_secret']
            ACCESS_TOKEN = keys['access_token']
            ACCESS_TOKEN_SECRET = keys['access_token_secret']
        

        # Get data & settings from UI
        keywords = self.dlg.keywords.text().lower().replace(', ', ',').split(',')
        max_tweets = self.dlg.nmbr_tweets.value()

        stop_time = False
        stop_time_text = str(stop_time)
        if self.dlg.time_day.value() and \
           self.dlg.time_hour.value() and \
           self.dlg.time_minute.value():
            stop_time = datetime.now().replace( \
                day = self.dlg.time_day.value(), \
                hour = self.dlg.time_hour.value(),\
                minute = self.dlg.time_minute.value())
            stop_time_text = str(stop_time)[8:-10]
        
        locations = [self.dlg.location_lon_from.value(),
                     self.dlg.location_lat_from.value(),
                     self.dlg.location_lon_to.value(),
                     self.dlg.location_lat_to.value()]
        
        search_method = self.dlg.search_method.currentText()
        output_metadata = self.dlg.output_metadata.currentText()

        output_GeoJSON = self.dlg.output_file_GeoJSON.isChecked()
        output_Shapefile = self.dlg.output_file_Shapefile.isChecked()
        output_QGIS = self.dlg.output_file_QGIS.isChecked()


        class streamAPI(StreamListener):

            def on_data(self, data):
                if not hasattr(streamAPI, '_requests'):
                    streamAPI._requests = 0
                    streamAPI._geo_tweets = 0
                    if output_GeoJSON:
                        open(file_name + '.geojson', 'w').write('{"type":"FeatureCollection","features":[')
                    if output_Shapefile:
                        shp = shapefile.Writer(shapefile.POINT) # create a point shapefile
                        shp.autoBalance = 1 # for every record there must be a corresponding geometry
                        
                        # create the field names and data type for each.
                        if output_metadata == 'Minimum (created_at, text, coordinates)':
                            field = ['created_at', 'text']
                        elif output_metadata == 'All (need more RAM / big files)':
                            field = [
                                'created_at', 'id', 'id_str', 'text', 'source', 'truncated', \
                                'in_reply_to_status_id', 'in_reply_to_status_id_str', \
                                'in_reply_to_user_id', 'in_reply_to_user_id_str', \
                                'in_reply_to_screen_name', 'geo', 'coordinates', \
                                'place', 'contributors', 'is_quote_status', 'retweet_count', \
                                'favorite_count', 'entities', 'favorited', 'retweeted', \
                                'filter_level', 'lang', 'timestamp_ms']
                        elif output_metadata == 'None - Only coordinates':
                            field = []

                        for i in range(len(field)):
                            shp.field(field[i].upper(), 'C')


                jdata = json.loads(data)
                streamAPI._requests += 1

                if streamAPI._requests % 50 == 0:
                    print_info(streamAPI._geo_tweets, streamAPI._requests)
                
                # Stop if timeout
                if stop_time and \
                stop_time.day == datetime.now().day and \
                stop_time.hour <= datetime.now().hour and \
                stop_time.minute <= datetime.now().minute:
                    save_file(output_GeoJSON, output_Shapefile, output_QGIS, shp)
                    print_info(streamAPI._geo_tweets, streamAPI._requests, 'Timeout: Done ')
                    return False

                # Skip 'limit'-messages & non geotweets
                if 'limit' in jdata or \
                        (not jdata['place'] and not jdata['geo']):
                    return True

                # Skip tweets without keywords
                for i in range(len(keywords)):
                    if keywords[i] in jdata['text'].lower():
                        break
                    else:
                        return True


                geo_tweet = '\n\t{ "type": "Geotweet", \n\t\t"geometry":\n\t\t\t'
                if not jdata['geo']: # Place
                    # Change Polygon to Point
                    coordinates = jdata['place']['bounding_box']['coordinates'][0]
                    lon = (coordinates[0][0] + coordinates[2][0]) / 2
                    lat = (coordinates[0][1] + coordinates[2][1]) / 2
                    geo_tweet += '{"type": "Point", "coordinates": [' + str(lon) + ', ' + str(lat) + ']}'
                else: # Geo
                    geo_tweet += str(jdata["geo"]).replace("u'", '"').replace("'", '"')

                # Add metadata which user choose
                geo_tweet += ',\n\t\t"properties": \n\t\t\t'
                if output_metadata == 'Minimum (created_at, text, coordinates)':
                    min_data = '"created_at":"' + str(jdata['created_at']) + '",' + \
                                '"text":"' + str(jdata['text'].encode('utf-8'))\
                                .replace('"', "'").replace('\\', "\\\\") + '"' # crutch-escape characters
                    geo_tweet += '{' + min_data + '}\n'
                elif output_metadata == 'All (need more RAM / big files)':
                    geo_tweet += data
                elif output_metadata == 'None - Only coordinates':
                    geo_tweet += '{}'
                geo_tweet += '\t}'

                if output_GeoJSON:
                    open(file_name + '.geojson', 'a').write(geo_tweet + ',')
                if output_Shapefile:
                    # access the GeoJSON tweet
                    reader = json.loads(geo_tweet)
                    a = {}
                    longitude = reader['geometry']['coordinates'][0]
                    latitude = reader['geometry']['coordinates'][1]
                    QgsMessageLog.logMessage('geom','logs')
                    for i in range(len(field)):
                        QgsMessageLog.logMessage(str({field[i]: str(reader['properties'][field[i]])\
                            .replace('\\', '').replace("u'", '').replace("'", '')}),'logs')
                        a.update({field[i]: str(reader['properties'][field[i]])\
                            .replace('\\', '').replace("u'", '').replace("'", '')})
                    QgsMessageLog.logMessage('for','logs')
                    # create the point geometry
                    shp.point(float(longitude), float(latitude))
                    # add attribute data
                    if output_metadata == 'Minimum (created_at, text, coordinates)':
                        shp.record(a['created_at'], a['text'])
                    elif output_metadata == 'All (need more RAM / big files)':
                        shp.record(\
                            a['created_at'], a['id'], a['id_str'], a['text'], a['source'], a['truncated'], \
                            a['in_reply_to_status_id'], a['in_reply_to_status_id_str'], \
                            a['in_reply_to_user_id'], a['in_reply_to_user_id_str'], \
                            a['in_reply_to_screen_name'], a['geo'], a['coordinates'], \
                            a['place'], a['contributors'], a['is_quote_status'], a['retweet_count'], \
                            a['favorite_count'], a['entities'], a['favorited'], a['retweeted'], \
                            a['filter_level'], a['lang'], a['timestamp_ms']\
                            )
                    elif output_metadata == 'None - Only coordinates':
                        shp.record()


                streamAPI._geo_tweets += 1
                if streamAPI._geo_tweets == max_tweets:
                    if output_GeoJSON:
                        open(file_name + '.geojson', 'a').write('\n]}')
                    if output_Shapefile:
                        shp.save(file_name) # save the Shapefile

                        prj = open(file_name + '.prj', 'w') # create the .prj file
                        epsg = getWKT_PRJ('4326') # call the function and supply the epsg code
                        prj.write(epsg)
                        prj.close()
                    print_info(streamAPI._geo_tweets, streamAPI._requests, 'Done ')
                    return False

                return True

            def on_error(self, status):
                QgsMessageLog.logMessage('ERROR ' + str(status), 'ERRORS')
                if status == 420:
                    QgsMessageLog.logMessage('Exceed a limit requests connect to' + \
                    'the streaming API in a window of time (15min)', 'ERRORS')
                    return False  # Returning False in on_data disconnects the stream

        # function to generate .prj file information using spatialreference.org
        def getWKT_PRJ (epsg_code):
            import urllib
            # access projection information
            wkt = urllib.urlopen('http://spatialreference.org/ref/epsg/{0}/prettywkt/'.format(epsg_code))
            remove_spaces = wkt.read().replace(' ','') # remove spaces between charachters
            output = remove_spaces.replace('\n', '') # place all the text on one line
            return output

        def print_info(_geo_tweets, _requests, msg=''):
            QgsMessageLog.logMessage(\
                msg + 'collect: ' + str(_geo_tweets) + '/' + str(max_tweets) + \
                ' | Requests: ' + str(_requests) + \
                ' | Worktime: ' + str(datetime.now() - start_time)[:-7] + \
                ' | Timeout: ' + stop_time_text, "Search GeoTweets")

        def save_file(output_GeoJSON, output_Shapefile, output_QGIS, shp):
            if output_GeoJSON:
                open(file_name + '.geojson', 'a').write('\n]}')
            if output_Shapefile:
                shp.save(file_name) # save the Shapefile

                prj = open(file_name + '.prj', 'w') # create the .prj file
                epsg = getWKT_PRJ('4326') # call the function and supply the epsg code
                prj.write(epsg)
                prj.close()



        start_time = datetime.now()
        file_name = str(self.plugin_dir) + '/Save files/' + str(start_time)[:-7].replace(':', '-')

        # Start tweepy
        auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

        if search_method == 'Realtime (Streaming API)':
            stream = Stream(auth, streamAPI())
            stream.filter(locations=locations, async=True)
      
        #Open Log Messages Panel for display print_info
        logDock = self.iface.mainWindow().findChild(QDockWidget, 'MessageLog')
        logDock.show()
