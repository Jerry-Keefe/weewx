#
#    Copyright (c) 2019 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Test aggregate functions."""

from __future__ import absolute_import
from __future__ import print_function

import configobj
import logging
import os.path
import sys
import time
import unittest

import gen_fake_data
import weeutil.logger
import weewx
import weewx.xtypes
import weewx.manager
from weeutil.weeutil import TimeSpan
from weewx.units import ValueTuple

weewx.debug = 1

log = logging.getLogger(__name__)
# Set up logging using the defaults.
weeutil.logger.setup('test_aggregate', {})

# Find the configuration file. It's assumed to be in the same directory as me:
config_path = os.path.join(os.path.dirname(__file__), "testgen.conf")


class TestAggregate(unittest.TestCase):

    def setUp(self):
        global config_path

        try:
            self.config_dict = configobj.ConfigObj(config_path, file_error=True, encoding='utf-8')
        except IOError:
            sys.stderr.write("Unable to open configuration file %s" % config_path)
            # Reraise the exception (this will eventually cause the program to exit)
            raise
        except configobj.ConfigObjError:
            sys.stderr.write("Error while parsing configuration file %s" % config_path)
            raise

        # This will generate the test databases if necessary. Use the SQLite database: it's faster.
        gen_fake_data.configDatabases(self.config_dict, database_type='sqlite')

    def tearDown(self):
        pass

    def test_get_aggregate(self):
        # Use the same function to test calculating aggregations from the main archive file, as well
        # as from the daily summaries:
        self.examine_object(weewx.xtypes.AggregateArchive)
        self.examine_object(weewx.xtypes.AggregateDaily)

    def examine_object(self, aggregate_obj):
        with weewx.manager.open_manager_with_config(self.config_dict, 'wx_binding') as db_manager:
            month_start_tt = (2010, 3, 1, 0, 0, 0, 0, 0, -1)
            month_stop_tt = (2010, 4, 1, 0, 0, 0, 0, 0, -1)
            start_ts = time.mktime(month_start_tt)
            stop_ts = time.mktime(month_stop_tt)

            avg_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'avg', db_manager)
            self.assertAlmostEqual(avg_vt[0], 28.74, 2)
            self.assertEqual(avg_vt[1], 'degree_F')
            self.assertEqual(avg_vt[2], 'group_temperature')

            max_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'max', db_manager)
            self.assertAlmostEqual(max_vt[0], 58.97, 2)
            maxtime_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'maxtime', db_manager)
            self.assertEqual(maxtime_vt[0], 1270087200)

            min_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'min', db_manager)
            self.assertAlmostEqual(min_vt[0], -.94, 2)
            mintime_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'mintime', db_manager)
            self.assertEqual(mintime_vt[0], 1267452000)

            count_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'count', db_manager)
            self.assertEqual(count_vt[0], 4396)

            sum_vt = aggregate_obj.get_aggregate('rain', TimeSpan(start_ts, stop_ts), 'sum', db_manager)
            self.assertAlmostEqual(sum_vt[0], 7.68, 2)

            # The AggregateArchive version has a few extra aggregate types:
            if aggregate_obj == weewx.xtypes.AggregateArchive:
                first_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'first', db_manager)
                # Get the timestamp of the first record inside the month
                ts = start_ts + gen_fake_data.interval
                rec = db_manager.getRecord(ts)
                self.assertEqual(first_vt[0], rec['outTemp'])

                first_time_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'firsttime', db_manager)
                self.assertEqual(first_time_vt[0], ts)

                last_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'last', db_manager)
                # Get the timestamp of the last record of the month
                rec = db_manager.getRecord(stop_ts)
                self.assertEqual(last_vt[0], rec['outTemp'])

                last_time_vt = aggregate_obj.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'lasttime', db_manager)
                self.assertEqual(last_time_vt[0], stop_ts)

                # Use 'dateTime' to check 'diff' and 'tderiv'. The calculations are super easy.
                diff_vt = aggregate_obj.get_aggregate('dateTime', TimeSpan(start_ts, stop_ts), 'diff', db_manager)
                self.assertEqual(diff_vt[0], stop_ts - start_ts)

                tderiv_vt = aggregate_obj.get_aggregate('dateTime', TimeSpan(start_ts, stop_ts), 'tderiv', db_manager)
                self.assertAlmostEqual(tderiv_vt[0], 1.0)

    def test_AggregateDaily(self):
        with weewx.manager.open_manager_with_config(self.config_dict, 'wx_binding') as db_manager:
            month_start_tt = (2010, 3, 1, 0, 0, 0, 0, 0, -1)
            month_stop_tt = (2010, 4, 1, 0, 0, 0, 0, 0, -1)
            start_ts = time.mktime(month_start_tt)
            stop_ts = time.mktime(month_stop_tt)

            min_ge_vt = weewx.xtypes.AggregateDaily.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'min_ge',
                                                            db_manager,
                                                            val=ValueTuple(15, 'degree_F', 'group_temperature'))
            self.assertEqual(min_ge_vt[0], 6)

            min_le_vt = weewx.xtypes.AggregateDaily.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'min_le',
                                                            db_manager,
                                                            val=ValueTuple(0, 'degree_F', 'group_temperature'))
            self.assertEqual(min_le_vt[0], 2)

            minmax_vt = weewx.xtypes.AggregateDaily.get_aggregate('outTemp', TimeSpan(start_ts, stop_ts), 'minmax',
                                                            db_manager)
            self.assertAlmostEqual(minmax_vt[0], 39.36, 2)

            max_wind_vt = weewx.xtypes.AggregateDaily.get_aggregate('wind', TimeSpan(start_ts, stop_ts), 'max', db_manager)
            self.assertAlmostEqual(max_wind_vt[0], 24.0, 2)

            avg_wind_vt = weewx.xtypes.AggregateDaily.get_aggregate('wind', TimeSpan(start_ts, stop_ts), 'avg', db_manager)
            self.assertAlmostEqual(avg_wind_vt[0], 10.21, 2)
            # Double check this last one against the average calculated from the archive
            avg_wind_vt = weewx.xtypes.AggregateArchive.get_aggregate('windSpeed', TimeSpan(start_ts, stop_ts), 'avg', db_manager)
            self.assertAlmostEqual(avg_wind_vt[0], 10.21, 2)

            vecavg_wind_vt = weewx.xtypes.AggregateDaily.get_aggregate('wind', TimeSpan(start_ts, stop_ts), 'vecavg',
                                                                 db_manager)
            self.assertAlmostEqual(vecavg_wind_vt[0], 5.14, 2)

            vecdir_wind_vt = weewx.xtypes.AggregateDaily.get_aggregate('wind', TimeSpan(start_ts, stop_ts), 'vecdir',
                                                                 db_manager)
            self.assertAlmostEqual(vecdir_wind_vt[0], 88.74, 2)

    def test_get_aggregate_heatcool(self):
        with weewx.manager.open_manager_with_config(self.config_dict, 'wx_binding') as db_manager:
            month_start_tt = (2010, 3, 1, 0, 0, 0, 0, 0, -1)
            month_stop_tt = (2010, 4, 1, 0, 0, 0, 0, 0, -1)
            start_ts = time.mktime(month_start_tt)
            stop_ts = time.mktime(month_stop_tt)

            # First, with the default heating base:
            heatdeg = weewx.xtypes.AggregateHeatCool.get_aggregate('heatdeg', TimeSpan(start_ts, stop_ts), 'sum', db_manager)
            self.assertAlmostEqual(heatdeg[0], 1123.99, 2)
            # Now with an explicit heating base:
            heatdeg = weewx.xtypes.AggregateHeatCool.get_aggregate('heatdeg', TimeSpan(start_ts, stop_ts), 'sum',
                                                             db_manager,
                                                             skin_dict={'Units': {'DegreeDays': {
                                                                 'heating_base': (60.0, "degree_F", "group_temperature")
                                                             }}})
            self.assertAlmostEqual(heatdeg[0], 968.99, 2)


if __name__ == '__main__':
    unittest.main()
