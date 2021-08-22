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

from unmanic.libs.unplugins.settings import PluginSettings

from lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.encoder_video_h264_nvenc")


class Settings(PluginSettings):
    settings = {
        "advanced":              False,
        "hw_decoding":           False,
        "max_muxing_queue_size": 2048,
        "preset":                "medium",
        "profile":               "main",
        "manual_pixel_format":   False,
        "pixel_format":          "yuv420p",
        "manual_bitrate":        False,
        "bitrate":               2,
        "main_options":          "",
        "advanced_options":      "",
        "custom_options":        "-preset medium\n"
                                 "-profile:v main\n"
                                 "-pix_fmt p010le\n"
                                 "-rc:v vbr_hq\n"
                                 "-qmin 0\n"
                                 "-rc-lookahead 32\n"
                                 "-spatial_aq:v 1\n"
                                 "-aq-strength:v 8\n"
                                 "-a53cc 0\n"
                                 "-b:v:0 4M\n",
    }

    def __init__(self):
        self.form_settings = {
            "advanced":              {
                "label": "Write your own FFmpeg params",
            },
            "hw_decoding":           self.__set_hw_decoding_checkbox_form_settings(),
            "max_muxing_queue_size": self.__set_max_muxing_queue_size_form_settings(),
            "preset":                self.__set_preset_form_settings(),
            "profile":               self.__set_profile_form_settings(),
            "manual_pixel_format":   self.__set_manual_pixel_format_checkbox_form_settings(),
            "pixel_format":          self.__set_pixel_format_form_settings(),
            "manual_bitrate":        self.__set_manual_bitrate_checkbox_form_settings(),
            "bitrate":               self.__set_bitrate_form_settings(),
            "main_options":          self.__set_main_options_form_settings(),
            "advanced_options":      self.__set_advanced_options_form_settings(),
            "custom_options":        self.__set_custom_options_form_settings(),
        }

    def __set_hw_decoding_checkbox_form_settings(self):
        values = {
            "label":      "Enable NVDEC HW Accelerated Decoding?",
            "input_type": "checkbox",
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_max_muxing_queue_size_form_settings(self):
        values = {
            "label":          "Max input stream packet buffer",
            "input_type":     "slider",
            "slider_options": {
                "min": 1024,
                "max": 10240,
            },
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

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

    def __set_manual_pixel_format_checkbox_form_settings(self):
        values = {
            "label":      "Manually select pixel format",
            "input_type": "checkbox",
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_pixel_format_form_settings(self):
        values = {
            "label":          "Pixel Format",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "yuv420p",
                    'label': "yuv420p - planar YUV 4:2:0, 12bpp, (1 Cr & Cb sample per 2x2 Y samples)",
                },
                {
                    'value': "nv12",
                    'label': "nv12 - planar YUV 4:2:0, 12bpp, 1 plane for Y and 1 plane for the UV components, which are interleaved (first byte U and the following byte V)",
                },
                {
                    'value': "p010",
                    'label': "p010 - like NV12, with 10bpp per component, data in the high bits, zeros in the low bits",
                },
                {
                    'value': "yuv444p",
                    'label': "yuv444p - planar YUV 4:4:4, 24bpp, (1 Cr & Cb sample per 1x1 Y samples)",
                },
                {
                    'value': "p016",
                    'label': "p016 - like NV12, with 16bpp per component",
                },
                {
                    'value': "yuv444p16",
                    'label': "yuv444p16 - planar YUV 4:4:4, 48bpp, (1 Cr & Cb sample per 1x1 Y samples)",
                },
            ],
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        elif not self.get_setting('manual_pixel_format'):
            values["display"] = 'hidden'
        return values

    def __set_manual_bitrate_checkbox_form_settings(self):
        values = {
            "label":      "Manually set bitrate",
            "input_type": "checkbox",
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_bitrate_form_settings(self):
        values = {
            "label":          "Bitrate (In MB)",
            "input_type":     "slider",
            "slider_options": {
                "min":    1,
                "max":    8,
                "suffix": "M"
            }
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        elif not self.get_setting('manual_bitrate'):
            values["display"] = 'hidden'
        return values

    def __set_main_options_form_settings(self):
        values = {
            "label":      "Write your own custom main options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_advanced_options_form_settings(self):
        values = {
            "label":      "Write your own custom advanced options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_custom_options_form_settings(self):
        values = {
            "label":      "Write your own custom video options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values


class PluginStreamMapper(StreamMapper):
    def __init__(self):
        super(PluginStreamMapper, self).__init__(logger, 'video')

    def test_stream_needs_processing(self, stream_info: dict):
        if stream_info.get('codec_name').lower() in ['h264']:
            return False
        return True

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        settings = Settings()

        if settings.get_setting('advanced'):
            stream_encoding = ['-c:v:{}'.format(stream_id), 'h264_nvenc']
            stream_encoding += settings.get_setting('custom_options').split()
        else:
            stream_encoding = [
                '-c:v:{}'.format(stream_id), 'h264_nvenc',
                '-profile:v:{}'.format(stream_id), settings.get_setting('profile'),
                '-preset', settings.get_setting('preset'),
                '-rc:v', 'vbr_hq',
                '-qmin', '0',
                '-rc-lookahead', '32',
                '-spatial_aq:v', '1',
                '-aq-strength:v', '8',
                '-a53cc', '0'
            ]
            if settings.get_setting('manual_pixel_format'):
                stream_encoding += ['-pix_fmt', str(settings.get_setting('pixel_format'))]
            if settings.get_setting('manual_bitrate'):
                stream_encoding += ['-b:v:{}'.format(stream_id), "{}M".format(settings.get_setting('bitrate'))]

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
    probe = Probe(logger)
    probe.file(abspath)

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_probe(probe)

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
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:
    
    """
    # Default to not run the FFMPEG command unless streams are found to be converted
    data['exec_command'] = []
    data['repeat'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Get file probe
    probe = Probe(logger)
    probe.file(abspath)

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_probe(probe)

    if mapper.streams_need_processing():
        settings = Settings()

        # Build ffmpeg args and add them to the return data
        data['exec_command'] = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel',
            'info',
            '-strict', '-2',
        ]

        if settings.get_setting('advanced'):
            data['exec_command'] += settings.get_setting('main_options').split()
        else:
            # Enable HW decoding?
            if settings.get_setting('hw_decoding'):
                data['exec_command'] += [
                    '-hwaccel', 'cuda',
                    '-hwaccel_output_format', 'cuda',
                ]

            # Set threads as one for slow conversions - produces better quality
            if settings.get_setting('preset') in ['fast', 'medium']:
                data['exec_command'] += ['-threads', '4']
            else:
                data['exec_command'] += ['-threads', '1']

        # Add file in
        data['exec_command'] += ['-i', data.get('file_in')]

        if settings.get_setting('advanced'):
            data['exec_command'] += settings.get_setting('advanced_options').split()
        else:
            data['exec_command'] += ['-max_muxing_queue_size', str(settings.get_setting('max_muxing_queue_size'))]

        # Add the stream mapping and the encoding args
        data['exec_command'] += mapper.get_stream_mapping()
        data['exec_command'] += mapper.get_stream_encoding()

        # Do not remux the file. Keep the file out in the same container
        split_file_in = os.path.splitext(data.get('file_in'))
        split_file_out = os.path.splitext(data.get('file_out'))
        data['file_out'] = "{}{}".format(split_file_out[0], split_file_in[1])

        data['exec_command'] += ['-y', data.get('file_out')]

        # Set the parser
        parser = Parser(logger)
        parser.set_probe(probe)

        data['command_progress_parser'] = parser.parse_progress

    return data
