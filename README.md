#Tweets

##Installation guide

1. Clone this repo to `/home/%username%/.qgis/python/plugins`

2. Install dependencies
```bash
$ pip install tweepy pyshp
```

3. Open `QGIS` -> `Plugins`-> `Manage and Install Plugins...` -> `Settings`. Check `Show also experimental plugins`.

4. In the same window, go to tab `All`, find plugin `SearchGeoTweets` and click `Install plugin`.

5. For run plugin, select menu `Web` -> `Search GeoTweets` -> `Run`, choose your parameters and click `OK`.

If you run plugin in first time, you need create [Twitter App](https://apps.twitter.com/) how it describe it [this guide](https://smashballoon.com/custom-twitter-feeds/docs/create-twitter-app/) and add keys to `Twitter Api` fields.

## Functional

For more information about all fields and features of plugin, please [goto wiki page](https://github.com/MaxymVlasov/Tweets/wiki/%5BUA%5D-%D0%A4%D1%83%D0%BD%D0%BA%D1%86%D1%96%D0%BE%D0%BD%D0%B0%D0%BB) (now only in Ukrainian).
