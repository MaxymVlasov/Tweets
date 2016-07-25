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
 This script initializes the plugin, making it known to QGIS.
"""
def name(): 
  return "Search Geo Tweets" 
def description():
  return "This is work and extended analog of geotweet"
def version(): 
  return "Version 0.1" 
def qgisMinimumVersion():
  return "2.0"
def classFactory(iface): 
  # load Tweets class from file Tweets
  from Tweets import Tweets 
  return Tweets(iface)
