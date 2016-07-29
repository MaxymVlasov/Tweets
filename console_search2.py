# -*- coding: utf-8 -*-

import json
import shapefile
from datetime import datetime
from tweepy import Stream, OAuthHandler
from tweepy.streaming import StreamListener
from keys import keys

CONSUMER_KEY = keys['consumer_key']
CONSUMER_SECRET = keys['consumer_secret']
ACCESS_TOKEN = keys['access_token']
ACCESS_TOKEN_SECRET = keys['access_token_secret']


# Get data & settings from UI
keywords = ''
max_tweets = 100

stop_time = False
stop_time_text = str(stop_time)

locations = [-180, -90, 180, 90]

search_method = 'Realtime (Streaming API)'
output_metadata = 'All (need more RAM / big files)'

output_GeoJSON = False
output_Shapefile = True
output_QGIS = False


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
            print 'geom'
            for field in fields:
                print str({field: str(reader['properties'][field])
                          .replace('\\', '').replace("u'", '').replace("'", '')})
                a.update({field: str(reader['properties'][field])
                         .replace('\\', '').replace("u'", '').replace("'", '')})
            print 'for'
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
        print 'ERROR ' + str(status), 'ERRORS'
        if status == 420:
            print 'Exceed a limit requests connect to the streaming API' + \
                  'in a window of time (15min)', 'ERRORS'
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
    print \
        msg + 'collect: ' + str(_geo_tweets) + '/' + str(max_tweets) + \
        ' | Requests: ' + str(_requests) + \
        ' | Worktime: ' + str(datetime.now() - start_time)[:-7] + \
        ' | Timeout: ' + stop_time_text


def save_file(output_GeoJSON, output_Shapefile, output_QGIS, shp):
    if output_GeoJSON:
        open(file_name + '.geojson', 'a').write('\n]}')
    if output_Shapefile:
        shp.save(file_name)  # save the Shapefile

        prj = open(file_name + '.prj', 'w')  # create the .prj file
        epsg = getWKT_PRJ('4326')  # call the function and supply the epsg code
        prj.write(epsg)
        prj.close()


start_time = datetime.now()
file_name = 'tmp-app2'

# Start tweepy
auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

if search_method == 'Realtime (Streaming API)':
    stream = Stream(auth, StreamAPI())
    stream.filter(locations=locations, async=True)
