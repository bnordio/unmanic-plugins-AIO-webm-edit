#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic-plugins.plugin.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     30 Jul 2021, (9:34 AM)

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
logger = logging.getLogger("Unmanic.Plugin.encoder_video_libvpx_vp9")


class Settings(PluginSettings):
    settings = {
        "mode":    "average_bitrate",
        "crf":     "31",
        "bitrate": "2M",
        "deadline": "good",
        "cpu-used": "0",
    }
    form_settings = {
        "mode":    {
            "label":          "Encoding Mode",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "average_bitrate",
                    'label': "Variable Bitrate (VBR)",
                },
                {
                    'value': "constant_quality",
                    'label': "Constant Quantizer (Q)",
                },
                {
                    'value': "constrained_quality",
                    'label': "Constrained Quality (CQ)",
                },
                {
                    'value': "constant_bitrate",
                    'label': "Constant Bitrate (CBR)",
                },
                {
                    'value': "lossless",
                    'label': "Lossless VP9",
                },
            ],
        },
        "crf":     {
            "label":         "Constant Rate Factor (CRF)",
            "input_type":    "range",
            "range_options": {
                "min": 0,
                "max": 63,
            },
        },
        "bitrate": {
            "label": "Bitrate",
        },
        "deadline": {
            "label":          "Deadline / Quality",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "good",
                    'label': "good",
                },
                {
                    'value': "best",
                    'label': "best",
                },
                {
                    'value': "realtime",
                    'label': "realtime",
                },
            ],
        },
        "cpu-used": {
            "label":         "CPU Utilization / Speed",
            "input_type":    "range",
            "range_options": {
                "min": 0,
                "max": 5,
            },
        },
    }


class StreamMapper(FfmpegStreamMapper):
    def __init__(self):
        super(StreamMapper, self).__init__(logger, 'video')

    def test_stream_needs_processing(self, stream_info: dict):
        if stream_info.get('codec_name').lower() in ['vp9']:
            return False
        return True

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        settings = Settings()
        # Default settings for 'Average Bitrate' encoder mode
        stream_encoding = ['-c:v:{}'.format(stream_id), 'libvpx-vp9', '-b:v', '2M']

        # Set stream encoder bitrate
        encoder_mode = settings.get_setting('mode')
        if encoder_mode == 'average_bitrate':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), 'libvpx-vp9',
                '-b:v:{}'.format(stream_id), settings.get_setting('bitrate'),
                '-threads', '8',
                '-row-mt', '1',
                '-deadline', settings.get_setting('deadline'),
                '-cpu-used', settings.get_setting('cpu-used')
            ]
        elif encoder_mode == 'constant_quality':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), 'libvpx-vp9',
                '-crf', settings.get_setting('crf'),
                '-b:v:{}'.format(stream_id), '0',
                '-threads', '8',
                '-row-mt', '1',
                '-deadline', settings.get_setting('deadline'),
                '-cpu-used', settings.get_setting('cpu-used')
            ]
        elif encoder_mode == 'constrained_quality':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), 'libvpx-vp9',
                '-crf', settings.get_setting('crf'),
                '-b:v:{}'.format(stream_id), settings.get_setting('bitrate'),
                '-threads', '8',
                '-row-mt', '1',
                '-deadline', settings.get_setting('deadline'),
                '-cpu-used', settings.get_setting('cpu-used')
            ]
        elif encoder_mode == 'constant_bitrate':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), 'libvpx-vp9',
                '-minrate', settings.get_setting('bitrate'),
                '-maxrate', settings.get_setting('bitrate'),
                '-b:v:{}'.format(stream_id), settings.get_setting('bitrate'),
                '-threads', '8',
                '-row-mt', '1',
                '-deadline', settings.get_setting('deadline'),
                '-cpu-used', settings.get_setting('cpu-used')
            ]
        elif encoder_mode == 'lossless':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), 'libvpx-vp9',
                '-lossless', '1',
                '-threads', '8',
                '-row-mt', '1',
                '-deadline', settings.get_setting('deadline'),
                '-cpu-used', settings.get_setting('cpu-used')
            ]

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
        mapper.streams_need_processing()
        # File does not contain streams to process
        data['exec_ffmpeg'] = True
        # Build ffmpeg args and add them to the return data
        data['ffmpeg_args'] = [
            '-i',
            data.get('file_in'),
            '-hide_banner',
            '-loglevel',
            'info',
        ]
        # Add the stream mapping and the encoding args
        data['ffmpeg_args'] += mapper.get_stream_mapping()
        data['ffmpeg_args'] += mapper.get_stream_encoding()

        # Do not remux the file. Keep the file out in the same container
        split_file_in = os.path.splitext(data.get('file_in'))
        split_file_out = os.path.splitext(data.get('file_out'))
        data['file_out'] = "{}{}".format(split_file_out[0], split_file_in[1])

        data['ffmpeg_args'] += ['-y', data.get('file_out')]

    return data
