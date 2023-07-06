#!/usr/bin/env python3

import argparse
import collections
import sqlite3

# Columns returned by the Tempest API for CSV-format results.
COLUMNS = (
    "device_id",
    "type",
    "bucket_step_minutes",
    "timestamp",
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
    device_id="INTEGER",
    type="TEXT",
    bucket_step_minutes="INTEGER",
    timestamp="INTEGER",
    precip_type="TEXT",
    precip_analysis_type="TEXT",
)

CREATE_WEATHER_TABLE_SQL_STATEMENT = f"""
CREATE TABLE IF NOT EXISTS weather (
  {', '.join('%s %s' % (col, COLUMN_SQL_TYPES[col]) for col in COLUMNS)}
);
""".strip()


def _parse_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        prog="sync_weather",
        description="Sync Tempest personal weather data with a local database.",
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
    return parser.parse_args()


def _open_database(path):
    """Opens the weather database at `path`, creating it if needed."""
    con = sqlite3.connect(path)
    with con:
        con.execute(CREATE_WEATHER_TABLE_SQL_STATEMENT)
    return con


def main():
    args = _parse_args()
    con = _open_database(args.database)
    print(args)


if __name__ == "__main__":
    main()
