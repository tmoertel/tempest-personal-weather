#!/usr/bin/env python3

"""Sync Tempest weather station data from the cloud to a local SQLite3 database.

Author: Tom Moertel <tom@moertel.com>
Created: July 2023

This command-line tool downloads your Tempest personal weather station data at
1-minute resolution from the cloud, saving it in a local SQLite3 database of your
choosing. The data will be saved to a table called `weather`. The table and the
database will be created if they do not exist.

The first time you run the tool, it will download the entire available history for
your weather station device(s). From then on, it will only download what it needs. (At
minimum, the tool downloads the most recent 24 hours' data for each device. This
allows it to update your local database with any revisions that may have been posted
to data you've previously downloaded.)

Example usage:

  # Sync data for two weather station devices.
  sync_weather.py \
    --api_token "replace this text with your actual API token" \
    --database $HOME/weather.db \
    --device_id 123456 789012

  # Compute the record count for each device by querying the database.
  sqlite3 $HOME/weather.db '
    SELECT device_id, COUNT(*) AS record_count
    FROM weather
    GROUP BY 1
    '

To get an API token for your personal weather stations, see "Getting Started" at
https://weatherflow.github.io/Tempest/api/.

If you want to keep a database synchronized, you can run the tool hourly as a cron
job. For example, the following crontab entry will run the tool to sync data for the
devices 123 and 456:

    1~30 * * * * $HOME/bin/sync_weather.py --api_token abc...def --database $HOME/weather.db --device_id 123 456

This crontab entry assumes that you have copied the sync_weather.py executable to your
$HOME/bin directory. If you've installed it elsewhere, update the entry accordingly.

"""

import argparse
import collections
import csv
import logging
import sqlite3
import time
import urllib.parse
import urllib.request

# Columns returned by the Tempest API for CSV-format results.
COLUMNS = (
    "device_id",
    "timestamp",
    "type",
    "bucket_step_minutes",
    "wind_lull",
    "wind_avg",
    "wind_gust",
    "wind_dir",
    "wind_interval",
    "pressure",
    "temperature",
    "humidity",
    "lux",
    "uv",
    "solar_radiation",
    "precip",
    "precip_type",
    "strike_distance",
    "strike_count",
    "battery",
    "report_interval",
    "local_daily_precip",
    "precip_final",
    "local_daily_precip_final",
    "precip_analysis_type",
)

# Create a map from column name to SQL types.
COLUMN_SQL_TYPES = collections.defaultdict(
    # Most columns hold real numbers.
    lambda: "REAL",
    # These columns hold data of other types.
    bucket_step_minutes="INTEGER",
    device_id="INTEGER NOT NULL",
    precip_analysis_type="TEXT",
    precip_type="TEXT",
    timestamp="INTEGER NOT NULL",
    type="TEXT",
)

# SQL statement used to initialize the `weather` table if needed.
CREATE_WEATHER_TABLE_SQL_TEMPLATE = f"""
CREATE TABLE IF NOT EXISTS weather (
  {', '.join('%s %s' % (col, COLUMN_SQL_TYPES[col]) for col in COLUMNS)},
  PRIMARY KEY (device_id, timestamp)
);
""".strip()

# SQL statement used to insert weather data into the database.
# We allow inserted rows to replace existing rows for the same device and
# timestamp because we want to allow for the possibility that Tempest
# may revise data, and we prefer the most-recent version of any data we
# already have.
INSERT_WEATHER_DATA_SQL_TEMPLATE = f"""
REPLACE INTO weather VALUES ({', '.join(':%s' % (col,) for col in COLUMNS)});
""".strip()

# SQL statement used to identify gaps in the time series for a device.
# We expect rows at 60-second intervals, but allow for up to nearly twice
# that amount to allow for a little slop in the timestamps.
SELECT_GAPS_SQL_TEMPLATE = f"""
WITH
  Deltas AS (
    SELECT
      LAG(timestamp) OVER win AS start_timestamp,
      timestamp AS end_timestamp,
      timestamp - LAG(timestamp) OVER win AS delta_seconds
    FROM weather
    WHERE device_id = ?
    WINDOW win AS (PARTITION BY device_id ORDER BY timestamp)
  )
  SELECT * FROM Deltas WHERE delta_seconds > 119;
""".strip()


# The number of seconds in a day.
ONE_DAY_IN_SECONDS = 24 * 3600


def _parse_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        prog="sync_weather",
        description="Sync Tempest personal weather data with a local database.",
    )
    parser.add_argument(
        "--api_token",
        required=True,
        help="Tempest API token to use when making API requests.",
    )
    parser.add_argument(
        "--database",
        required=True,
        help="Path to the sqlite3 database to use; it will be created if needed.",
    )
    parser.add_argument(
        "--device_id",
        required=True,
        nargs="+",
        type=int,
        help="The id(s) of the device(s) to sync data for.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Emit progress information.",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )

    return parser.parse_args()


def _open_database(path):
    """Opens the weather database at `path`, creating it if needed."""
    con = sqlite3.connect(path)
    with con:
        con.execute(CREATE_WEATHER_TABLE_SQL_TEMPLATE)
    return con


def _most_recent_device_timestamp(device_id, con):
    """Gets the most-recent timestamp for a device in the database."""
    with con:
        (max_timestamp,) = con.execute(
            "SELECT MAX(timestamp) FROM weather WHERE device_id = ?", (device_id,)
        ).fetchone()
    # If we have no saved data for the device, we return 0 ("the start of time").
    if max_timestamp is None:
        return 0
    return max_timestamp


def _sync_device(api_token, device_id, con):
    """Syncs the device given by `device_id` to the database open on `con`."""
    # Compute the time range we want to fill with data from the Tempest API.
    logging.info("syncing data for device %d", device_id)
    most_recent_timestamp = _most_recent_device_timestamp(device_id, con)
    end_timestamp = int(time.time())  # Now.
    logging.info(
        "device %d has most_recent_timestamp = %d", device_id, most_recent_timestamp
    )
    # Sync at least 24 hours of data to allow Tempest the chance to revise recent data.
    start_timestamp = min(most_recent_timestamp, end_timestamp - ONE_DAY_IN_SECONDS)
    _sync_device_for_range(api_token, device_id, con, start_timestamp, end_timestamp)


def _sync_device_for_range(api_token, device_id, con, start_timestamp, end_timestamp):
    """Syncs data for a device over a time range."""
    range_start = start_timestamp

    # Work backward to the start of the range.
    while range_start < end_timestamp:
        # Limit each request to one days' data; otherwise, we won't get 1-minute resolution.
        start_timestamp = max(end_timestamp - ONE_DAY_IN_SECONDS, range_start)
        logging.info(
            "fetching data for device %d: timestamp range (%d, %d)",
            device_id,
            start_timestamp,
            end_timestamp,
        )
        data_rows = _fetch_device_data_for_range(
            api_token, device_id, start_timestamp, end_timestamp
        )
        # Exit the loop if we've exhausted the data from Tempest.
        if not data_rows:
            break
        # Write the data to the weather database.
        _write_data_for_device(con, data_rows)
        logging.info("wrote %d rows for device %d", len(data_rows), device_id)
        # And continue with the next chunk of data.
        end_timestamp = start_timestamp

    logging.info("finished sync for device %d", device_id)


def _q(value):
    """Quotes a value for inclusion in a URL."""
    return urllib.parse.quote(f"{value}")


def _fetch_device_data_for_range(api_token, device_id, start_timestamp, end_timestamp):
    """Fetches weather data for a device over a range to time.

    Args:
      api_token: An Tempest API token authorized to gather data for the device.

      device_id: The id of the personal weather station for which to fetch the data.

      start_timestamp: The start of the range in seconds since the epoch.

      end_timestamp: The end of the range in seconds since the epoch.

    Returns a list of time-series entries, with each entry being a dict that maps
    column names to their corresponding values, as returned by the Tempest API.
    (The expected column names are those given in the `COLUMNS` global variable.)

    """
    url = (
        f"https://swd.weatherflow.com/swd/rest/observations/device/{_q(device_id)}"
        f"?time_start={_q(start_timestamp)}"
        f"&time_end={_q(end_timestamp)}"
        f"&format=csv"
        f"&token={_q(api_token)}"
    )
    csv_table = urllib.request.urlopen(url).read().decode("utf-8")
    data_rows = csv.DictReader(csv_table.splitlines())
    return list(data_rows)


def _write_data_for_device(con, data_rows):
    """Writes data rows for a device to the database on `con`.

    Note: The `data_rows`, as returned by the Tempest API, already contain
    the `device_id`, so there is no need to pass it to this function.

    """
    with con:
        con.executemany(INSERT_WEATHER_DATA_SQL_TEMPLATE, data_rows)


def main():
    args = _parse_args()
    logging.basicConfig(level=args.loglevel)
    con = _open_database(args.database)
    for device_id in args.device_id:
        _sync_device(args.api_token, device_id, con)


if __name__ == "__main__":
    main()
