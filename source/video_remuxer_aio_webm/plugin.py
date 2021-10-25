#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Oct 2021, (10:01 AM)

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
import json
import logging
import mimetypes
import os
from pprint import pprint

import psutil
from unmanic.libs.unplugins.settings import PluginSettings

from video_remuxer_aio_webm.lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.video_remuxer_aio_webm")


class Settings(PluginSettings):
    """
    WebM containers can contain:
        - Video: VP8, VP9, AV1
        - Audio: Opus or Vorbis
        - Subtitles: WebVVT
    """

    settings = {
        "video_codec":                 "vp9",
        "auto_video_encoder_settings": True,
        "video_encoder_mode":          "average_bitrate",
        "crf":                         "31",
        "bitrate":                     "2",
        "deadline":                    "good",
        "cpu_used":                    "0",
        "audio_codec":                 "opus",
        "subtitle_codec":              "webvtt",
    }

    def __init__(self):
        self.form_settings = {
            "video_codec":                 self.__set_video_codec_settings(),
            "auto_video_encoder_settings": self.__set_auto_video_encoder_settings_settings(),
            "video_encoder_mode":          self.__set_video_encoder_mode_settings(),
            "crf":                         self.__set_crf_settings(),
            "bitrate":                     self.__set_bitrate_settings(),
            "deadline":                    self.__set_deadline_settings(),
            "cpu_used":                    self.__set_cpu_used_settings(),
            "audio_codec":                 self.__set_audio_codec_settings(),
            "subtitle_codec":              self.__set_subtitle_codec_settings(),
        }

    # __     _____ ____  _____ ___
    # \ \   / /_ _|  _ \| ____/ _ \
    #  \ \ / / | || | | |  _|| | | |
    #   \ V /  | || |_| | |__| |_| |
    #    \_/  |___|____/|_____\___/
    #
    def __set_video_codec_settings(self):
        values = {
            "label":          "Video Encoder",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "vp9",
                    'label': "VP9",
                },
                {
                    'value': "vp8",
                    'label': "VP8",
                },
            ],
        }
        return values

    def __set_auto_video_encoder_settings_settings(self):
        values = {
            "label": "Auto calculate the best video encoder settings based on source bitrate",
        }
        if self.get_setting('video_codec') in ['vp8']:
            values["display"] = 'hidden'
        return values

    def __set_video_encoder_mode_settings(self):
        values = {
            "label":          "Video Encoding Mode",
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
        }
        if self.get_setting('auto_video_encoder_settings') or self.get_setting('video_codec') in ['vp8']:
            values["display"] = 'hidden'
        return values

    def __set_crf_settings(self):
        values = {
            "label":          "Video Constant Rate Factor (CRF)",
            "input_type":     "slider",
            "slider_options": {
                "min": 0,
                "max": 63,
            },
        }
        if self.get_setting('auto_video_encoder_settings') or self.get_setting('video_codec') in ['vp8']:
            values["display"] = 'hidden'
        elif self.get_setting('video_encoder_mode') in ['average_bitrate', 'constant_bitrate', 'lossless']:
            values["display"] = 'hidden'
        return values

    def __set_bitrate_settings(self):
        values = {
            "label":          "Video Bitrate",
            "input_type":     "slider",
            "slider_options": {
                "min":    1000,
                "max":    10000,
                "step":   100,
                "suffix": "K"
            },
        }
        if self.get_setting('auto_video_encoder_settings') or self.get_setting('video_codec') in ['vp8']:
            values["display"] = 'hidden'
        elif self.get_setting('video_encoder_mode') in ['constant_quality', 'lossless']:
            values["display"] = 'hidden'
        return values

    def __set_deadline_settings(self):
        values = {
            "label":          "Video Encoder Deadline / Quality",
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
        }
        return values

    def __set_cpu_used_settings(self):
        values = {
            "label":          "Video Encoder CPU Utilization / Speed",
            "input_type":     "slider",
            "slider_options": {
                "min": 0,
                "max": 5,
            },
        }
        return values

    #     _   _   _ ____ ___ ___
    #    / \ | | | |  _ \_ _/ _ \
    #   / _ \| | | | | | | | | | |
    #  / ___ \ |_| | |_| | | |_| |
    # /_/   \_\___/|____/___\___/
    #
    def __set_audio_codec_settings(self):
        values = {
            "label":          "Audio Encoder",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "opus",
                    'label': "Opus",
                }
            ],
        }
        return values

    #  ____  _   _ ____ _____ ___ _____ ___ _     _____
    # / ___|| | | | __ )_   _|_ _|_   _|_ _| |   | ____|
    # \___ \| | | |  _ \ | |  | |  | |  | || |   |  _|
    #  ___) | |_| | |_) || |  | |  | |  | || |___| |___
    # |____/ \___/|____/ |_| |___| |_| |___|_____|_____|
    #
    def __set_subtitle_codec_settings(self):
        values = {
            "label":          "Subtitle Encoder",
            "input_type":     "select",
            "select_options": [
                {
                    'value': "webvtt",
                    'label': "WebVVT",
                }
            ],
        }
        return values


class PluginStreamMapper(StreamMapper):
    def __init__(self):
        super(PluginStreamMapper, self).__init__(logger, ['video', 'audio', 'subtitle', 'data', 'attachment'])
        self.settings = None
        self.container_data = None
        self.filter_complex = []

    def test_stream_needs_processing(self, stream_info: dict):
        if not self.settings:
            self.settings = Settings()

        # Test all stream types
        if stream_info.get('codec_type').lower() == "video":
            if stream_info.get('codec_name').lower() not in [self.settings.get_setting('video_codec')]:
                return True
        elif stream_info.get('codec_type').lower() == "audio":
            if stream_info.get('codec_name').lower() not in [self.settings.get_setting('audio_codec')]:
                return True
        elif stream_info.get('codec_type').lower() == "subtitle":
            if stream_info.get('codec_name').lower() not in [self.settings.get_setting('audio_codec')]:
                return True

        return False

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        ident = {
            'video':      'v',
            'audio':      'a',
            'subtitle':   's',
            'data':       'd',
            'attachment': 't'
        }
        codec_type = stream_info.get('codec_type').lower()

        if not self.settings:
            self.settings = Settings()

        if stream_info.get('codec_type').lower() == "video":
            if self.settings.get_setting('video_codec') == 'vp9':
                stream_encoding = self.__vp9_stream_encoding_args(stream_info, stream_id)
            elif self.settings.get_setting('video_codec') == 'vp8':
                stream_encoding = self.__vp8_stream_encoding_args(stream_info, stream_id)
            else:
                stream_encoding = self.__vp9_stream_encoding_args(stream_info, stream_id)
            return {
                'stream_mapping':  ['-map', '0:{}:{}'.format(ident.get(codec_type), stream_id)],
                'stream_encoding': stream_encoding,
            }

        elif stream_info.get('codec_type').lower() == "audio":
            stream_encoding = self.__opus_stream_encoding_args(stream_info, stream_id)
            return {
                'stream_mapping':  ['-map', '0:{}:{}'.format(ident.get(codec_type), stream_id)],
                'stream_encoding': stream_encoding,
            }

        elif stream_info.get('codec_type').lower() == "subtitle":
            # Remove all image based subs
            image_subtitle_codecs = [
                'dvbsub',
                'dvb_subtitle',
                'dvdsub',
                'dvd_subtitle',
                'pgssub',
                'hdmv_pgs_subtitle',
                'xsub',
            ]
            if stream_info.get('codec_name').lower() in image_subtitle_codecs:
                return {
                    'stream_mapping':  [],
                    'stream_encoding': []
                }

            # Transcode all text based subs
            stream_encoding = self.__webvvt_stream_encoding_args(stream_info, stream_id)
            return {
                'stream_mapping':  ['-map', '0:{}:{}'.format(ident.get(codec_type), stream_id)],
                'stream_encoding': stream_encoding,
            }

        # Stream is not compatible with WebM
        return {
            'stream_mapping':  [],
            'stream_encoding': []
        }

    # def apply_filter_complex(self):
    #     """
    #     Applies a complex channel mapping filter (and other filters if added)
    #
    #     :return:
    #     """
    #     advanced_kwargs = {
    #         "-filter_complex": ''.join(self.filter_complex),
    #     }
    #     self.set_ffmpeg_advanced_options(**advanced_kwargs)

    # __     _____ ____  _____ ___
    # \ \   / /_ _|  _ \| ____/ _ \
    #  \ \ / / | || | | |  _|| | | |
    #   \ V /  | || |_| | |__| |_| |
    #    \_/  |___|____/|_____\___/
    #
    def __calculate_source_video_bitrate(self, percent):
        # Get format bitrate
        bit_rate = self.probe.get('format', {}).get('bit_rate')
        if not bit_rate:
            # TODO: If format fails, get the bitrate by calculating the whole video size
            bit_rate = 1000000

        value = (float(percent) * float(bit_rate))

        return int(value)

    def __vp9_stream_encoding_args(self, stream_info, stream_id):
        # Defaults
        stream_encoding = []
        threads = psutil.cpu_count()
        encoder = 'libvpx-vp9'

        # If plugin is to figure out best settings, return them here
        if self.settings.get_setting('auto_video_encoder_settings'):
            if stream_info.get('codec_name').lower() in ['h264']:
                # 60% of the original for H264
                video_bitrate = self.__calculate_source_video_bitrate(0.6)
            elif stream_info.get('codec_name').lower() in ['h265', 'hevc']:
                # 80% of the original for HEVC
                video_bitrate = self.__calculate_source_video_bitrate(0.8)
            else:
                # 50% of the original for all other older codes
                video_bitrate = self.__calculate_source_video_bitrate(0.5)

            twenty_percent_bitrate = int(video_bitrate * 0.4)
            video_minrate = int(float(video_bitrate) * 0.5)
            video_maxrate = int(float(video_bitrate) * 1.4)
            video_bufsize = int(float(video_maxrate) / 1.5)
            return [
                '-c:v:{}'.format(stream_id), encoder,
                '-minrate', str(video_minrate),
                '-maxrate', str(video_maxrate),
                '-bufsize', str(video_bufsize),
                '-b:v:{}'.format(stream_id), str(video_bitrate),
                '-threads', str(threads),
                '-row-mt', '1',
                '-deadline', self.settings.get_setting('deadline'),
                '-cpu-used', str(self.settings.get_setting('cpu_used'))
            ]

        # Set stream encoder bitrate
        encoder_mode = self.settings.get_setting('video_encoder_mode')
        if encoder_mode == 'average_bitrate':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), encoder,
                '-b:v:{}'.format(stream_id), '{}K'.format(self.settings.get_setting('bitrate')),
                '-threads', str(threads),
                '-row-mt', '1',
                '-deadline', self.settings.get_setting('deadline'),
                '-cpu-used', str(self.settings.get_setting('cpu_used'))
            ]
        elif encoder_mode == 'constant_quality':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), encoder,
                '-crf', str(self.settings.get_setting('crf')),
                '-b:v:{}'.format(stream_id), '0',
                '-threads', str(threads),
                '-row-mt', '1',
                '-deadline', self.settings.get_setting('deadline'),
                '-cpu-used', str(self.settings.get_setting('cpu_used'))
            ]
        elif encoder_mode == 'constrained_quality':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), encoder,
                '-crf', str(self.settings.get_setting('crf')),
                '-b:v:{}'.format(stream_id), '{}K'.format(self.settings.get_setting('bitrate')),
                '-threads', str(threads),
                '-row-mt', '1',
                '-deadline', self.settings.get_setting('deadline'),
                '-cpu-used', str(self.settings.get_setting('cpu_used'))
            ]
        elif encoder_mode == 'constant_bitrate':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), encoder,
                '-minrate', '{}K'.format(self.settings.get_setting('bitrate')),
                '-maxrate', '{}K'.format(self.settings.get_setting('bitrate')),
                '-b:v:{}'.format(stream_id), '{}K'.format(self.settings.get_setting('bitrate')),
                '-threads', str(threads),
                '-row-mt', '1',
                '-deadline', self.settings.get_setting('deadline'),
                '-cpu-used', str(self.settings.get_setting('cpu_used'))
            ]
        elif encoder_mode == 'lossless':
            stream_encoding = [
                '-c:v:{}'.format(stream_id), encoder,
                '-lossless', '1',
                '-threads', str(threads),
                '-row-mt', '1',
                '-deadline', self.settings.get_setting('deadline'),
                '-cpu-used', str(self.settings.get_setting('cpu_used'))
            ]

        return stream_encoding

    def __vp8_stream_encoding_args(self, stream_info, stream_id):
        # Defaults
        threads = psutil.cpu_count()
        encoder = 'libvpx'

        # If plugin is to figure out best settings, return them here
        if stream_info.get('codec_name').lower() in ['h264']:
            # 60% of the original for H264
            video_bitrate = self.__calculate_source_video_bitrate(0.6)
        elif stream_info.get('codec_name').lower() in ['h265', 'hevc']:
            # 80% of the original for HEVC
            video_bitrate = self.__calculate_source_video_bitrate(0.8)
        else:
            # 50% of the original for all other older codes
            video_bitrate = self.__calculate_source_video_bitrate(0.5)

        twenty_percent_bitrate = int(video_bitrate * 0.4)
        video_minrate = int(float(video_bitrate) * 0.5)
        video_maxrate = int(float(video_bitrate) * 1.4)
        video_bufsize = int(float(video_maxrate) / 1.5)
        return [
            '-c:v:{}'.format(stream_id), encoder,
            '-minrate', str(video_minrate),
            '-maxrate', str(video_maxrate),
            '-bufsize', str(video_bufsize),
            '-b:v:{}'.format(stream_id), str(video_bitrate),
            '-threads', str(threads),
            '-row-mt', '1',
            '-deadline', self.settings.get_setting('deadline'),
            '-cpu-used', str(self.settings.get_setting('cpu_used'))
        ]

    #     _   _   _ ____ ___ ___
    #    / \ | | | |  _ \_ _/ _ \
    #   / _ \| | | | | | | | | | |
    #  / ___ \ |_| | |_| | | |_| |
    # /_/   \_\___/|____/___\___/
    #
    def __opus_stream_encoding_args(self, stream_info, stream_id):
        """
        Configure the OPUS encoder
        REFS:
            https://wiki.xiph.org/Opus_Recommended_Settings

        :param stream_info:
        :return:
        """
        # Defaults
        encoder = 'libopus'

        channels = stream_info.get('channels', 2)
        # Determine bitrate based on source channel count
        if int(channels) <= 8:
            audio_bitrate = '{}k'.format((int(channels) * 40))
            logger.debug(
                "Audio stream channel count ({}). Setting OPUS bit rate to {}.".format(channels, audio_bitrate))
        # elif int(channels) == 7:
        #     audio_bitrate = '{}k'.format((int(channels) * 40))
        #     logger.debug(
        #         "Audio stream channel count is 7 exactly. Setting OPUS bit rate to {}.".format(audio_bitrate))
        # elif int(channels) >= 8:
        #     logger.debug("Audio stream channel count ({}) is >= 8. Setting max OPUS bit rate (450k).".format(channels))
        #     audio_bitrate = '450k'
        else:
            # Default to best quality
            logger.debug(
                "Stream 'bit_rate' could not be matched directly ({}). Setting max OPUS bit rate.".format(channels))
            audio_bitrate = '450k'

        stream_encoding = [
            '-c:a:{}'.format(stream_id), encoder,
            '-b:a:{}'.format(stream_id), str(audio_bitrate),
            '-ac:a:{}'.format(stream_id), '{}'.format(channels)
        ]

        # # Fix channel layout mapping
        # channel_layout = stream_info.get('channel_layout', '')
        # channelmap_layouts = [
        #     "3.0",
        #     "3.1",
        #     "4.0",
        #     "4.1",
        #     "5.0",
        #     "5.1",
        #     "6.0",
        #     "6.1",
        #     "7.0",
        #     "7.1"
        # ]
        # channel_layout = channel_layout.replace('(side)', '')
        # if channel_layout in channelmap_layouts:
        #     self.filter_complex.append('-filter:a:{}'.format(stream_id, channel_layout))
        #     # stream_encoding += [
        #     #     '-filter:a:{}'.format(stream_id)
        #     # ]
        # elif channel_layout in ['stereo']:
        #     self.filter_complex.append('[{}:a]channelmap=channel_layout=stereo[left][right]'.format(stream_id))

        return stream_encoding

    #  ____  _   _ ____ _____ ___ _____ ___ _     _____
    # / ___|| | | | __ )_   _|_ _|_   _|_ _| |   | ____|
    # \___ \| | | |  _ \ | |  | |  | |  | || |   |  _|
    #  ___) | |_| | |_) || |  | |  | |  | || |___| |___
    # |____/ \___/|____/ |_| |___| |_| |___|_____|_____|
    #
    def __webvvt_stream_encoding_args(self, stream_info, stream_id):
        return [
            '-c:a:{}'.format(stream_id), 'webvtt'
        ]


def correct_mimetypes():
    mimetypes.add_type('video/x-m4v', '.m4v')


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
    correct_mimetypes()
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    if mapper.container_needs_remuxing('webm'):
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug(
            "File '{}' should be added to task list. Probe found file needs to be remuxed.".format(abspath))
    elif mapper.streams_need_processing():
        logger.debug(
            "File '{}' should be added to task list. Probe found streams need to be processed.".format(abspath))
    else:
        logger.debug("File '{}' is already the required format.".format(abspath))

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
    correct_mimetypes()
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    container_extension = 'webm'
    if mapper.streams_need_processing() or mapper.container_needs_remuxing(container_extension):
        # Set the input file
        mapper.set_input_file(abspath)

        # # Apply the complex filters
        # mapper.apply_filter_complex()

        # Set the output file
        split_file_out = os.path.splitext(data.get('file_out'))
        new_file_out = "{}.{}".format(split_file_out[0], container_extension.lstrip('.'))
        mapper.set_output_file(new_file_out)
        data['file_out'] = new_file_out

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
