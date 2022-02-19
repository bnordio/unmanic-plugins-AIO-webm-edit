#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     16 Nov 2021, (07:01 AM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""

import logging
import os
import time
from configparser import NoSectionError, NoOptionError

import humanfriendly
from unmanic.libs.unplugins.settings import PluginSettings
from unmanic.libs.directoryinfo import UnmanicDirectoryInfo

# Configure plugin logger
from ffmpeg_file_error_checker.lib.ffmpeg import StreamMapper, Probe, Parser

logger = logging.getLogger("Unmanic.Plugin.ffmpeg_file_error_checker")


class Settings(PluginSettings):
    settings = {
        "decoding_type":         'software',
        "max_muxing_queue_size": 2048,
        "retest_files":          False,
        "test_frequency":        '4 weeks',
        "always_run":            True,
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "decoding_type":         {
                "label":          "Enable HW Accelerated Decoding?",
                "input_type":     "select",
                "select_options": [
                    {
                        'value': "software",
                        'label': "Software",
                    },
                    {
                        'value': "vaapi",
                        'label': "VAAPI HW Accelerated Decoding",
                    },
                    {
                        'value': "nvdec",
                        'label': "NVIDIA HW Accelerated Decoding",
                    },
                ],
            },
            "max_muxing_queue_size": {
                "label":          "Max input stream packet buffer",
                "input_type":     "slider",
                "slider_options": {
                    "min": 1024,
                    "max": 10240,
                },
            },
            "retest_files":          {
                "label": "Enable retesting of files?",
            },
            "test_frequency":        self.__set_test_frequency_form_settings(),
            "always_run":            {
                "label": "Always run this plugin against video files, even if that file was added to the task list by another plugin?",
            },
        }

    def __set_test_frequency_form_settings(self):
        values = {
            "label": "Frequency",
        }
        if not self.get_setting('retest_files'):
            values["display"] = 'hidden'
        return values


class PluginStreamMapper(StreamMapper):

    def __init__(self):
        super(PluginStreamMapper, self).__init__(logger, ['video'])

    @staticmethod
    def list_available_vaapi_devices():
        """
        Return a list of available VAAPI decoder devices
        :return:
        """
        decoders = []
        dir_path = os.path.join("/", "dev", "dri")

        if os.path.exists(dir_path):
            for device in sorted(os.listdir(dir_path)):
                if device.startswith('render'):
                    device_data = {
                        'hwaccel':        'vaapi',
                        'hwaccel_device': os.path.join("/", "dev", "dri", device),
                    }
                    decoders.append(device_data)

        # Return the list of decoders
        return decoders

    def generate_vaapi_decoding_args(self):
        """
        Generate a list of args for using a VAAPI decoder
        :return:
        """
        # Set the hardware device
        hardware_devices = self.list_available_vaapi_devices()
        if not hardware_devices:
            # Return no options. No hardware device was found
            raise Exception("No VAAPI device found")
        hardware_device = hardware_devices[0]
        # Set a named global device that can be used used with various params
        dev_id = 'vaapi0'
        # Configure args such that when the input may or may not be hardware decodable we can do:
        #   REF: https://trac.ffmpeg.org/wiki/Hardware/VAAPI#Encoding
        generic_kwargs = {
            "-init_hw_device":        "vaapi={}:{}".format(dev_id, hardware_device.get('hwaccel_device')),
            "-hwaccel":               "vaapi",
            "-hwaccel_output_format": "vaapi",
            "-hwaccel_device":        dev_id,
        }
        self.set_ffmpeg_generic_options(**generic_kwargs)

    def generate_nvdec_decoding_args(self):
        """
        Generate a list of args for using a NVDEC decoder
        :return:
        """
        # Set a named global device that can be used used with various params
        dev_id = '0'
        generic_kwargs = {
            "-hwaccel":        "cuda",
            "-hwaccel_device": dev_id,
        }
        self.set_ffmpeg_generic_options(**generic_kwargs)

    def generate_test_args(self, settings):
        """

        ffmpeg -hide_banner -loglevel error -stats -xerror -hwaccel vaapi -hwaccel_output_format vaapi -hwaccel_device /dev/dri/renderD128 -i "${1}" -max_muxing_queue_size 9999 -f null -

        :param settings:
        :return:
        """
        # Configure loglevel
        generic_args = [
            "-stats",
            "-xerror",
        ]
        generic_kwargs = {
            "-loglevel": "error",
        }
        self.set_ffmpeg_generic_options(*generic_args, **generic_kwargs)

        # Check if we are using a VAAPI encoder also...
        if settings.get_setting('decoding_type') == 'vaapi':
            self.generate_vaapi_decoding_args()
        elif settings.get_setting('decoding_type') == 'nvdec':
            self.generate_nvdec_decoding_args()

        advanced_kwargs = {
            '-max_muxing_queue_size': str(settings.get_setting('max_muxing_queue_size'))
        }
        self.set_ffmpeg_advanced_options(**advanced_kwargs)


def needs_testing(path, settings):
    """
    Ensure this file does not need to be added due to frequent retesting

    :param path:
    :param settings:
    :return:
    """
    directory_info = UnmanicDirectoryInfo(os.path.dirname(path))

    try:
        previous_tested = directory_info.get('ffmpeg_file_error_checker', os.path.basename(path))
    except NoSectionError as e:
        previous_tested = ''
    except NoOptionError as e:
        previous_tested = ''
    except Exception as e:
        logger.debug("Unknown exception {}.".format(e))
        previous_tested = ''

    if previous_tested:
        logger.debug("File was previously tested for errors on {}.".format(time.ctime(int(previous_tested))))
        # This stream already has been normalised
        if settings.get_setting('retest_files'):
            # Check if previous time was more recent than time now - frequency
            current_timestamp = time.time()
            test_frequency = settings.get_setting('test_frequency')
            timestamp_for_next_test = (int(previous_tested) + int(humanfriendly.parse_timespan(test_frequency)))
            if int(current_timestamp) > int(timestamp_for_next_test):
                return True
            return False

    # Default to...
    return True


def on_library_management_file_test(data):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Get the path to the file
    abspath = data.get('path')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_probe(probe)

    # Configure settings object
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    if needs_testing(abspath, settings):
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug(
            "File '{}' should be added to task list. File has not been tested within the configured days.".format(
                abspath))
    else:
        logger.debug("File '{}' does not require testing.".format(abspath))

    return data


def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:
    
    """
    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Check if this plugin should run every time against files or only when scheduled
    if settings.get_setting('retest_files') and not settings.get_setting('always_run'):
        logger.debug("Plugin configured to only run against video files that are required.")
        if not needs_testing(abspath, settings):
            # This video file has been tested within the configured frequency time
            return data

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    # File out to nowhere...
    mapper.set_output_null()

    # Set the test args
    mapper.generate_test_args(settings)

    # Get generated ffmpeg args
    ffmpeg_args = mapper.get_ffmpeg_args()

    # Apply ffmpeg args to command
    data['exec_command'] = ['ffmpeg']
    data['exec_command'] += ffmpeg_args

    # Set the parser
    parser = Parser(logger)
    parser.set_probe(probe)
    data['command_progress_parser'] = parser.parse_progress

    return data


def on_postprocessor_task_results(data):
    """
    Runner function - provides a means for additional postprocessor functions based on the task success.

    The 'data' object argument includes:
        task_processing_success         - Boolean, did all task processes complete successfully.
        file_move_processes_success     - Boolean, did all postprocessor movement tasks complete successfully.
        destination_files               - List containing all file paths created by postprocessor file movements.
        source_data                     - Dictionary containing data pertaining to the original source file.

    :param data:
    :return:

    """
    # We only care that the task completed successfully.
    # If a worker processing task was unsuccessful, dont mark the file as being tested.
    # If it failed the test, it would have failed the worker processing task stage
    if not data.get('task_processing_success'):
        return data

    # Configure settings object
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()
    # Loop over the destination_files list and update the directory info file for each one
    if settings.get_setting('retest_files'):
        current_timestamp = time.time()
        for destination_file in data.get('destination_files'):
            directory_info = UnmanicDirectoryInfo(os.path.dirname(destination_file))
            directory_info.set('ffmpeg_file_error_checker', os.path.basename(destination_file),
                               str(int(current_timestamp)))
            directory_info.save()
            logger.debug("Error check timestamp info written for '{}'.".format(destination_file))

    return data
