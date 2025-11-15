This directory contains an example [systemd](https://systemd.io/)
configuration for running the `sync_weather.py` script to collect
weather data from stations hourly.

It was kindly contributed by Tim Graettinger.

To use this service, you will need to edit the following scripts and install them:

* **.env** - the "secrets" file with your Tempest API token and the
  device id. (Note that this file has been named `env` here, without
  the dot, to make it easier to see in this example directory.)
* **run_sync.sh** - the shell script that invokes `sync_weather.py`.
* **tempest-sync.service** and **tempest-sync.timer** - the systemd
  service and timer for running hourly updates. These files are
  typically be installed in the `/etc/systemd/system` directory. (You
  could alternatively create a [user-based
  service](https://wiki.archlinux.org/title/Systemd/User), as opposed
  to a system-based service. Just beware that it may not run unless
  you are logged in.)

For general help on creating systemd services, see the [Red Hat
Enterprise Linux docs on Working with systemd unit
files](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_systemd_unit_files_to_customize_and_optimize_your_system/working-with-systemd-unit-files).
