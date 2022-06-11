#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.global_settings.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     10 Jun 2022, (6:52 PM)

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


class GlobalSettings:

    def __init__(self, settings):
        self.settings = settings

    def __set_default_option(self, select_options, key, default_option=None):
        """
        Sets the default option if the currently set option is not available

        :param select_options:
        :param key:
        :return:
        """
        available_options = []
        for option in select_options:
            available_options.append(option.get('value'))
            if not default_option:
                default_option = option.get('value')
        if self.settings.get_setting(key) not in available_options:
            self.settings.set_setting(key, default_option)

    def get_mode_form_settings(self):
        return {
            "label":          "Config mode",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "basic",
                    'label': "Basic (Not sure what I am doing. Configure most of it for me.)",
                },
                {
                    'value': "standard",
                    'label': "Standard (I know how to transcode some video. Let me tweak some settings.)",
                },
            ],
        }
        # TODO: Enable advanced options
        # {
        #     'value': "advanced",
        #     'label': "Advanced - Dont tell me what to do, I write FFmpeg commands in my sleep",
        # },

    def get_max_muxing_queue_size_form_settings(self):
        values = {
            "label":          "Max input stream packet buffer",
            "input_type":     "slider",
            "slider_options": {
                "min": 1024,
                "max": 10240,
            },
        }
        if self.settings.get_setting('mode') not in ['standard', 'advanced']:
            values["display"] = 'hidden'
        return values

    def get_video_codec_form_settings(self):
        return {
            "label":          "Video Codec",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "h264",
                    'label': "H264",
                },
                {
                    'value': "hevc",
                    'label': "HEVC/H265",
                },
            ],
        }

    def get_video_encoder_form_settings(self):
        values = {
            "label":          "Video Encoder",
            "input_type":     "select",
            "select_options": [],
        }
        if self.settings.get_setting('video_codec') == 'hevc':
            # TODO: Only enable VAAPI for Linux
            # TODO: Enable libx265
            values['select_options'] = [
                {
                    'value': "hevc_qsv",
                    'label': "QSV - hevc_qsv",
                },
                {
                    'value': "hevc_vaapi",
                    'label': "VAAPI - hevc_vaapi",
                },
            ]
        elif self.settings.get_setting('video_codec') == 'h264':
            # TODO: Add support for VAAPI (requires some tweaking of standard values)
            # TODO: Enable libx264
            values['select_options'] = [
                {
                    'value': "h264_qsv",
                    'label': "QSV - h264_qsv",
                },
            ]
        self.__set_default_option(values['select_options'], 'video_encoder')
        return values

    def get_main_options_form_settings(self):
        values = {
            "label":      "Write your own custom main options",
            "input_type": "textarea",
        }
        if self.settings.get_setting('mode') not in ['advanced']:
            values["display"] = 'hidden'
        return values

    def get_advanced_options_form_settings(self):
        values = {
            "label":      "Write your own custom advanced options",
            "input_type": "textarea",
        }
        if self.settings.get_setting('mode') not in ['advanced']:
            values["display"] = 'hidden'
        return values

    def get_custom_options_form_settings(self):
        values = {
            "label":      "Write your own custom video options",
            "input_type": "textarea",
        }
        if self.settings.get_setting('mode') not in ['advanced']:
            values["display"] = 'hidden'
        return values

    def get_keep_container_form_settings(self):
        return {
            "label": "Keep the same container",
        }

    def get_dest_container_form_settings(self):
        values = {
            "label":          "Set the output container",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "mkv",
                    'label': ".mkv - Matroska",
                },
                {
                    'value': "mp4",
                    'label': ".mp4 - MP4 (MPEG-4 Part 14)",
                },
            ],
        }
        if self.settings.get_setting('keep_container'):
            values["display"] = 'hidden'
        return values

    def get_autocrop_black_bars_form_settings(self):
        values = {
            "label": "Autocrop black bars",
        }
        if self.settings.get_setting('mode') not in ['standard']:
            values["display"] = 'hidden'
        return values
