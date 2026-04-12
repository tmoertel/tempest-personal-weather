# Tempest Personal Weather Tools
Tools for gathering and using data from a Tempest personal weather station.

This project provides a simple tool to download your weather data from a
[Tempest personal weather station](https://shop.weatherflow.com/products/tempest)
and keep it up to date.

**Author:** [Tom Moertel](https://blog.moertel.com/)\
**Project page:** https://github.com/tmoertel/tempest-personal-weather


## Features

* **Simple.** Just supply your API token, a path to a SQLite3
  database, and your Tempest device id(s). The tool will do the rest. It will create
  the database if needed and then download your historical weather data at 1-minute
  resolution using the Tempest API.
* **Smart.** If you've already downloaded your data before, the tool will only download
  new data. (Don't worry, it will always download the most-recent 24 hours' data to update
  any previously downloaded data that has been revised.)
* **Small.** The tool is implemented as a single, small Python script.
* **No dependencies beyond Python 3.** The tool requires only a reasonably up-to-date
  Python 3 installation with its normal sqlite3 and HTTPS support. It uses only packages
  in the [Python Standard Library](https://docs.python.org/3/library/).

**Tip:** To get an API token for your personal weather stations, see "Getting Started" at
https://weatherflow.github.io/Tempest/api/.

**Note on rate limiting:** If you have a substantial backlog of data to download, the
Tempest API may apply rate limiting, preventing you from downloading all of your data
in one attempt. If this happens, just wait a few hours and try again. The script will
automatically resume downloading where it left off. Just repeat this process as needed
to download your full backlog of historical data.


## License

This project is licensed under the GNU GPLv3. See the [LICENSE](LICENSE) file that came
with the project for the terms and conditions.


## Usage

Here's how you run the tool:

```
usage: sync_weather.py [-h] [-v] --api_token API_TOKEN --database DATABASE --device_id DEVICE_ID [DEVICE_ID ...]

Sync Tempest personal weather data with a local database.

options:
  -h, --help            show this help message and exit
  --api_token API_TOKEN
                        Tempest API token to use when making API requests.
  --database DATABASE   Path to the sqlite3 database to use; it will be created if needed.
  --device_id DEVICE_ID [DEVICE_ID ...]
                        The id(s) of the device(s) to sync data for.
  -v, --verbose         Emit progress information.
```

By default, the tool runs silently. Pass the `--verbose` option if you want it
to emit diagnostic output to show what it is doing.


## Examples

To synchronize data for the weather station devices having ids 123 and 456
to a local database at `$HOME/weather.db` you could use this command:

```sh
  # Sync data for two weather station devices 123 and 456.
  sync_weather.py \
    --api_token "replace this text with your actual API token" \
    --database $HOME/weather.db \
    --device_id 123 456
```

After the tool exits, the database will contain the weather history for the
two devices at 1-minute resolution. Now you can use normal data tools to
analyze your data.

For example, to see how many data points you have for each device, you can
run a simple SQL query directly against the database:

```sh
  # Compute the record count for each device by querying the database.
  sqlite3 $HOME/weather.db '
    SELECT device_id, COUNT(*) AS record_count
    FROM weather
    GROUP BY 1
    '
```


## Keeping your local weather database up to date

If you want to keep your database synchronized with the latest weather data, you can run
the tool hourly as a cron job. For example, the following crontab entry will run the
tool to sync data for the devices 123 and 456:

```crontab
1~30 * * * * $HOME/bin/sync_weather.py --api_token "your-token-here" --database $HOME/weather.db --device_id 123 456
```

Replace `your-token-here` with your actual API token.

This crontab entry assumes that you have copied the `sync_weather.py` executable to your
`$HOME/bin` directory. If you've installed it elsewhere, update the entry accordingly.


## Troubleshooting

If you are having problems, please consider the following advice.

### The script does not download all of your historical data when you set up your database

There are several potential causes of this problem:

* **Your API token is not registered as the owner of the device(s)
  whose data you are attempting to download.** According to
  [the Tempest API documentation](https://apidocs.tempestwx.com/reference/getobservationsbydeviceid#:~:text=Generally%2C%20a%20user%20can%20only%20query%20data%20for%20their%20own%20devices%2C%20using%20the%20API%20token%20associated%20with%20their%20account.%20Commercial%20users%20may%20be%20able%20to%20query%20all%20devices%20associated%20with%20a%20mesonet.),
  “Generally, a user can only query data for their own devices, using
  the API token associated with their account. Commercial users may be
  able to query all devices associated with a mesonet.” **Solution:**
  Obtain an authorized API token for the devices, and use it when you
  run the sync\_weather script.
* **You have been rate limited.** The Tempest API does not allow you
  to download a massive quantity of data at once. **Solution:** Wait a
  few hours, then rerun the script. The script will resume downloading
  where it left off. Continue this process until all historical data
  is downloaded. If the script is scheduled to run periodically (see
  the crontab recipe above), it should eventually download all
  historical data after a few iterations. If it still fails, proceed
  to the next potential cause (gaps).
* **There is a gap in your recorded data spanning more than 24
  hours.** The Tempest API does not provide a method to determine the
  earliest date of the data available for a device, so the script works
  backward, downloading one day’s data at a time until it hits a day
  having no data. If any of your devices failed to record data for
  more than 24 hours, the script will be unable to find its data
  earlier than the gap. **Solution:** There is no easy solution, but
  there is a workaround:
  * Starting with the most-recent gap—you must work in reverse
    chronological order—insert a dummy record into your weather
    database to indicate the start of the gap, then re-run the script.
    * To find the most-recent gap, use the Tempest app on your phone
      or on the web to search backward from the current day. When you
      find the gap, find the date of the first day without any data.
    * Convert this date into a Unix timestamp (the duration in seconds
      since January 1, 1970, 00:00 UTC). On Unix-like systems, you can
      use the **date** command to convert a date into a timestamp. For
      example, to convert April 3, 2026, you would use this command:
      `date --date='April 3, 2026' '+%s'` and it would emit the
      following output: `1775188800`
    * Insert a dummy record into the database for the device and
      timestamp. For example: `sqlite3 $HOME/weather.db "INSERT INTO
      weather (device_id, timestamp) VALUES (1234567, 1775188800);"`
      Remember to replace `$HOME/weather.db` with the path to your
      database, `1234567` with the ID of the device in question, and
      `1775188800` with the timestamp you found in the previous step.
  * Run the script, passing in  the `--verbose` option to observe what
    it downloads.
  * After it downloads the data before the gap, repeat the process for
    the next most-recent gap, working backward through the recorded
    data for the device.

### Other problems

To diagnose other problems, manually run the sync command, but add the
**\--verbose** option and **save the output to a file**. For example:

`$HOME/bin/sync_weather.py --verbose --api_token "$YOUR_API_TOKEN" --database $HOME/weather.db --device_id 1234567 >& diagnostics.txt`

Remember to replace $HOME/weather.db with the path to your database
and 1234567 with the ID of the device in question.

Inspect the `diagnostics.txt` file for clues.
