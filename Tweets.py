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
import os.path
import json
import shapefile
from datetime import datetime
from tweepy import Stream, OAuthHandler
from tweepy.streaming import StreamListener
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import QSettings, qVersion, QTranslator
from PyQt4.QtGui import QIcon, QAction, QDockWidget
from qgis.core import QCoreApplication, QgsMessageLog
import qgis.utils
# Import the code for the dialog
from TweetsDialog import TweetsDialog


class Tweets(object):

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

            if qVersion() > '4.3.3':  # FIX ME http://vk.cc/5r9Onz
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
        """Remove the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&Tweets'),
                action)
            self.iface.removeToolBarIcon(action)

        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""  # TODO: rewrite docstring

        # Create and show the dialog
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

        # Load new Twitter API keys
        keys = dict()
        keys['consumer_key'] = self.dlg.consumer_key.text()
        keys['consumer_secret'] = self.dlg.consumer_key_secret.text()
        keys['access_token'] = self.dlg.access_token.text()
        keys['access_token_secret'] = self.dlg.access_token_secret.text()

        # If have new Twitter API keys - Save
        if (keys['consumer_key'] and keys['consumer_secret'] and
           keys['access_token'] and keys['access_token_secret']):

            with open(os.path.join(self.plugin_dir, 'keys.json'), 'w') as keys_file:
                keys_file.write(json.dumps(keys))

        # If haven't new & previous Twitter API keys - Stop
        elif not all(keys.values()) and os.path.isfile('keys.json'):

            warning_message = qgis.utils.iface.messageBar().createMessage(
                'No Twitter API keys! Please, enter them and try again')
            qgis.utils.iface.messageBar().pushWidget(
                warning_message, qgis.utils.iface.messageBar().WARNING)
            return False

        # Load previous Twitter API keys
        else:
            with open(os.path.join(self.plugin_dir, 'keys.json'), 'r') as keys_file:
                keys = json.load(keys_file)

        # Get data & settings from UI
        keywords = self.dlg.keywords.text().lower().replace(', ', ',').split(',')
        max_tweets = self.dlg.nmbr_tweets.value()

        stop_time = False
        stop_time_text = str(stop_time)
        if (self.dlg.time_day.value() and
           self.dlg.time_hour.value() and
           self.dlg.time_minute.value()):
            stop_time = datetime.now().replace(
                day=self.dlg.time_day.value(),
                hour=self.dlg.time_hour.value(),
                minute=self.dlg.time_minute.value())
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

        class StreamAPI(StreamListener):

            def on_data(self, data):
                if not hasattr(StreamAPI, '_requests'):
                    StreamAPI._requests = 0
                    StreamAPI._geo_tweets = 0
                    if output_GeoJSON:
                        with open(file_name + '.geojson', 'w') as file:
                            file.write('{"type":"FeatureCollection","features":[')
                    if output_Shapefile:
                        shp = shapefile.Writer(shapefile.POINT)  # create a point shapefile
                        shp.autoBalance = 1  # for every record there must be a corresponding geometry

                        # create the fields names and data type for each.
                        if output_metadata == 'Minimum (created_at, text, coordinates)':
                            fields = ['created_at', 'text']
                        elif output_metadata == 'All (need more RAM / big files)':
                            fields = [
                                'created_at', 'id', 'id_str', 'text', 'source', 'truncated',
                                'in_reply_to_status_id', 'in_reply_to_status_id_str',
                                'in_reply_to_user_id', 'in_reply_to_user_id_str',
                                'in_reply_to_screen_name', 'geo', 'coordinates',
                                'place', 'contributors', 'is_quote_status', 'retweet_count',
                                'favorite_count', 'entities', 'favorited', 'retweeted',
                                'filter_level', 'lang', 'timestamp_ms']
                        elif output_metadata == 'None - Only coordinates':
                            fields = []

                        for field in fields:
                            shp.fields(field.upper(), 'C')

                jdata = json.loads(data)
                StreamAPI._requests += 1

                if StreamAPI._requests % 50 == 0:
                    print_info(StreamAPI._geo_tweets, StreamAPI._requests)

                # Stop if timeout
                time_now = datetime.now()
                if (stop_time and
                   stop_time.day == time_now.day and
                   stop_time.hour <= time_now.hour and
                   stop_time.minute <= time_now.minute):
                    save_file(output_GeoJSON, output_Shapefile, output_QGIS, shp)
                    print_info(StreamAPI._geo_tweets, StreamAPI._requests, 'Timeout: Done ')
                    return False

                # Skip 'limit'-messages & non geotweets
                if 'limit' in jdata or \
                        (not jdata['place'] and not jdata['geo']):
                    return True

                # Skip tweets without keywords
                for keyword in keywords:
                    if keyword in jdata['text'].lower():
                        break
                    else:
                        return True
                # TODO: http://vk.cc/5raROT
                geo_tweet = '\n\t{ "type": "Geotweet", \n\t\t"geometry":\n\t\t\t'
                if not jdata['geo']:  # Place
                    # Change Polygon to Point
                    coordinates = jdata['place']['bounding_box']['coordinates'][0]
                    lon = (coordinates[0][0] + coordinates[2][0]) / 2
                    lat = (coordinates[0][1] + coordinates[2][1]) / 2
                    geo_tweet += '{"type": "Point", "coordinates": [' + str(lon) + ', ' + str(lat) + ']}'
                else:  # Geo
                    geo_tweet += str(jdata['geo']).replace("u'", '"').replace("'", '"')

                # Add metadata which user choose
                geo_tweet += ',\n\t\t"properties": \n\t\t\t'
                if output_metadata == 'Minimum (created_at, text, coordinates)':
                    min_data = '"created_at":"' + str(jdata['created_at']) + '",' + \
                                '"text":"' + str(jdata['text'].encode('utf-8'))\
                                .replace('"', "'").replace('\\', '\\\\') + '"'  # crutch-escape characters
                    geo_tweet += '{' + min_data + '}\n'
                elif output_metadata == 'All (need more RAM / big files)':
                    geo_tweet += data
                elif output_metadata == 'None - Only coordinates':
                    geo_tweet += '{}'
                geo_tweet += '\t}'

                if output_GeoJSON:
                    with open(file_name + '.geojson', 'a') as file:
                        file.write(geo_tweet + ',')
                if output_Shapefile:
                    # access the GeoJSON tweet
                    reader = json.loads(geo_tweet)
                    a = {}
                    longitude = reader['geometry']['coordinates'][0]
                    latitude = reader['geometry']['coordinates'][1]
                    QgsMessageLog.logMessage('geom', 'logs')
                    for field in fields:
                        QgsMessageLog.logMessage(str({field: str(reader['properties'][field])
                                                     .replace('\\', '').replace("u'", '').replace("'", '')}), 'logs')
                        a.update({field: str(reader['properties'][field])
                                 .replace('\\', '').replace("u'", '').replace("'", '')})
                    QgsMessageLog.logMessage('for', 'logs')
                    # create the point geometry
                    shp.point(float(longitude), float(latitude))
                    # add attribute data
                    if output_metadata == 'Minimum (created_at, text, coordinates)':
                        shp.record(a['created_at'], a['text'])
                    elif output_metadata == 'All (need more RAM / big files)':
                        shp.record(
                            a['created_at'], a['id'], a['id_str'], a['text'], a['source'], a['truncated'],
                            a['in_reply_to_status_id'], a['in_reply_to_status_id_str'],
                            a['in_reply_to_user_id'], a['in_reply_to_user_id_str'],
                            a['in_reply_to_screen_name'], a['geo'], a['coordinates'],
                            a['place'], a['contributors'], a['is_quote_status'], a['retweet_count'],
                            a['favorite_count'], a['entities'], a['favorited'], a['retweeted'],
                            a['filter_level'], a['lang'], a['timestamp_ms']
                            )
                    elif output_metadata == 'None - Only coordinates':
                        shp.record()

                StreamAPI._geo_tweets += 1
                if StreamAPI._geo_tweets == max_tweets:
                    if output_GeoJSON:
                        with open(file_name + '.geojson', 'a') as file:
                            file.write('\n]}')
                    if output_Shapefile:
                        shp.save(file_name)  # save the Shapefile

                        with open(file_name + '.prj', 'w') as prj:  # create the .prj file
                            epsg = getWKT_PRJ('4326')  # call the function and supply the epsg code
                            prj.write(epsg)

                    print_info(StreamAPI._geo_tweets, StreamAPI._requests, 'Done ')
                    return False

                return True

            def on_error(self, status):
                QgsMessageLog.logMessage('ERROR ' + str(status), 'ERRORS')
                if status == 420:
                    QgsMessageLog.logMessage('Exceed a limit requests connect to the streaming API'
                                             'in a window of time (15min)', 'ERRORS')
                    return False  # Returning False in on_data disconnects the stream

        # function to generate .prj file information using spatialreference.org
        def getWKT_PRJ(epsg_code):
            import urllib
            # access projection information
            wkt = urllib.urlopen('http://spatialreference.org/ref/epsg/{0}/prettywkt/'.format(epsg_code))
            remove_spaces = wkt.read().replace(' ', '')  # remove spaces between charachters
            output = remove_spaces.replace('\n', '')  # place all the text on one line
            return output

        def print_info(_geo_tweets, _requests, msg=''):
            QgsMessageLog.logMessage(
                msg + 'collect: ' + str(_geo_tweets) + '/' + str(max_tweets) +
                ' | Requests: ' + str(_requests) +
                ' | Worktime: ' + str(datetime.now() - start_time)[:-7] +
                ' | Timeout: ' + stop_time_text, 'Search GeoTweets')

        def save_file(output_GeoJSON, output_Shapefile, output_QGIS, shp):
            if output_GeoJSON:
                open(file_name + '.geojson', 'a').write('\n]}')  # TODO: http://vk.cc/5raY2g
            if output_Shapefile:
                shp.save(file_name)  # save the Shapefile

                prj = open(file_name + '.prj', 'w')  # create the .prj file
                epsg = getWKT_PRJ('4326')  # call the function and supply the epsg code
                prj.write(epsg)
                prj.close()

        start_time = datetime.now()
        file_name = str(self.plugin_dir) + '/Save files/' + str(start_time)[:-7].replace(':', '-')
        # Start tweepy
        auth = OAuthHandler(keys['consumer_key'], keys['consumer_secret'])
        auth.set_access_token(keys['access_token'], keys['access_token_secret'])

        if search_method == 'Realtime (Streaming API)':
            stream = Stream(auth, StreamAPI())
            stream.filter(locations=locations, async=True)

        # Open Log Messages Panel for display print_info
        logDock = self.iface.mainWindow().findChild(QDockWidget, 'MessageLog')
        logDock.show()
