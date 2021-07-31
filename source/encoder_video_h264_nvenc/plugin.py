#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic-plugins.plugin.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     31 Jul 2021, (8:03 AM)

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
import sys

from unmanic.libs.unplugins.settings import PluginSettings

# handle import error (older versions of Unmanic did not include the plugin directory in the sys path
try:
    from lib.ffmpeg_stream_mapping import FfmpegStreamMapper
except ImportError:
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(plugin_dir) and plugin_dir not in sys.path:
        sys.path.append(plugin_dir)
    from lib.ffmpeg_stream_mapping import FfmpegStreamMapper

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.encoder_video_h264_nvenc")


class Settings(PluginSettings):
    settings = {
        "hw_decoding":  False,
        "preset":       "slow",
        "profile":      "high",
        "auto_bitrate": True,
        "bitrate":      2,
        "advanced":     "",
    }

    def __init__(self):
        self.form_settings = {
            "hw_decoding":  {
                "label": "Enable NVDEC HW Accelerated Decoding?",
            },
            "preset":       self.__set_preset_form_settings(),
            "profile":      self.__set_profile_form_settings(),
            "auto_bitrate": {
                "label": "Automatically set bitrate",
            },
            "bitrate":      self.__set_bitrate_form_settings(),
            "advanced":     {
                "label":      "Overwrite all options with custom input",
                "input_type": "textarea",
            },
        }

    def __set_preset_form_settings(self):
        values = {
            "label":          "NVENC Encoder Quality Preset",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "fast",
                    'label': "Fast",
                },
                {
                    'value': "medium",
                    'label': "Medium",
                },
                {
                    'value': "slow",
                    'label': "Slow",
                },
                {
                    'value': "lossless",
                    'label': "Lossless (slowest)",
                },
            ],
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_profile_form_settings(self):
        values = {
            "label":          "Profile",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "baseline",
                    'label': "Baseline",
                },
                {
                    'value': "main",
                    'label': "Main",
                },
                {
                    'value': "high",
                    'label': "High",
                },
                {
                    'value': "high444p",
                    'label': "High444p",
                },
            ],
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_bitrate_form_settings(self):
        values = {
            "label":         "Bitrate (In MB)",
            "input_type":    "range",
            "range_options": {
                "min":    1,
                "max":    8,
                "suffix": "M"
    }
        }
        if self.get_setting('auto_bitrate'):
            values["display"] = 'hidden'
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values


class StreamMapper(FfmpegStreamMapper):
    def __init__(self):
        super(StreamMapper, self).__init__(logger, 'video')

    def test_stream_needs_processing(self, stream_info: dict):
        if stream_info.get('codec_name').lower() in ['h264']:
            return False
        return True

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        settings = Settings()

        if settings.get_setting('advanced'):
            stream_encoding = ['-c:v:{}'.format(stream_id), 'h264_nvenc', ] + settings.get_setting('advanced').split()
        else:
            stream_encoding = [
                '-c:v:{}'.format(stream_id), 'h264_nvenc',
                '-profile:v:{}'.format(stream_id), settings.get_setting('profile'),
                '-preset', settings.get_setting('preset'),
                '-pix_fmt', 'p010le',
                '-rc:v', 'vbr_hq',
                '-qmin', '0',
                '-rc-lookahead', '32',
                '-spatial_aq:v', '1',
                '-aq-strength:v', '8',
                '-a53cc', '0'
            ]
            if not settings.get_setting('auto_bitrate'):
                stream_encoding += ['-b:v:{}'.format(stream_id), settings.get_setting('bitrate')]

        return {
            'stream_mapping':  ['-map', '0:v:{}'.format(stream_id)],
            'stream_encoding': stream_encoding,
        }


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
    mapper = StreamMapper()
    mapper.file_probe(abspath)

    if mapper.streams_need_processing():
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug("File '{}' should be added to task list. Probe found streams require processing.".format(abspath))
    else:
        logger.debug("File '{}' does not contain streams require processing.".format(abspath))

    return data


def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_ffmpeg             - Boolean, should Unmanic run FFMPEG with the data returned from this plugin.
        file_probe              - A dictionary object containing the current file probe state.
        ffmpeg_args             - A list of Unmanic's default FFMPEG args.
        file_in                 - The source file to be processed by the FFMPEG command.
        file_out                - The destination that the FFMPEG command will output.
        original_file_path      - The absolute path to the original library file.

    :param data:
    :return:
    
    """
    # Default to not run the FFMPEG command unless streams are found to be converted
    data['exec_ffmpeg'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Get file probe
    mapper = StreamMapper()
    mapper.file_probe(abspath)

    if mapper.streams_need_processing():
        settings = Settings()
        mapper.streams_need_processing()
        # File does not contain streams to process
        data['exec_ffmpeg'] = True
        # Build ffmpeg args and add them to the return data
        data['ffmpeg_args'] = [
            '-hide_banner',
            '-loglevel',
            'info',
        ]

        # Enable HW decoding?
        if settings.get_setting('hw_decoding'):
            data['ffmpeg_args'] += ['-hwaccel', 'cuvid']

        # Set threads as one for slow conversions - produces better quality
        if settings.get_setting('preset') in ['fast', 'medium']:
            data['ffmpeg_args'] += ['-threads', '4']
        else:
            data['ffmpeg_args'] += ['-threads', '1']

        # Add file in
        data['ffmpeg_args'] += ['-i', data.get('file_in')]

        # Add the stream mapping and the encoding args
        data['ffmpeg_args'] += mapper.get_stream_mapping()
        data['ffmpeg_args'] += mapper.get_stream_encoding()

        # Do not remux the file. Keep the file out in the same container
        split_file_in = os.path.splitext(data.get('file_in'))
        split_file_out = os.path.splitext(data.get('file_out'))
        data['file_out'] = "{}{}".format(split_file_out[0], split_file_in[1])

        data['ffmpeg_args'] += ['-y', data.get('file_out')]

    return data
