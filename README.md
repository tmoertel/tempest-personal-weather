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


## License

This project is licensed under the GNU GPLv3. See the [LICENSE](LICENSE) file that came
with the project for the terms and conditions.

