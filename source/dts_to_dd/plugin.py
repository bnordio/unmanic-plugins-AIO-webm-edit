#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic-plugins.plugin.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     04 Jun 2021, (7:10 PM)

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
import mimetypes
import os

from unmanic.libs import unffmpeg
from unmanic.libs.unplugins.settings import PluginSettings

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.dts_to_dd")


class Settings(PluginSettings):
    settings = {
        'downmix_dts_hd_ma': False
    }
    form_settings = {
        "downmix_dts_hd_ma": {
            "label": "Downmix DTS-HD Master Audio (max 5.1 channels)?",
        },
    }


def get_file_probe(file_path):
    # Ensure file exists
    if not os.path.exists(file_path):
        return {}

    # Only run this check against video/audio/image MIME types
    mimetypes.init()
    file_type = mimetypes.guess_type(file_path)[0]
    # If the file has no MIME type then it cannot be tested
    if file_type is None:
        return {}
    # Make sure the MIME type is either audio, video or image
    file_type_category = file_type.split('/')[0]
    if file_type_category not in ['audio', 'video', 'image']:
        return {}

    try:
        # Get the file probe info
        return unffmpeg.Info().file_probe(file_path)
    except unffmpeg.exceptions.ffprobe.FFProbeError as e:
        return {}
    except Exception as e:
        return {}


def should_process_dts_stream(probe_stream):
    settings = Settings()
    if probe_stream.get('profile').upper() == 'DTS':
        # Process all DTS tracks
        return True

    if probe_stream.get('profile').upper() == 'DTS-HD MA':
        # This stream is 
        if not settings.get_setting('destination downmix_dts_hd_ma'):
            return False

    # Default to 
    return False


def get_ac3_equivalent_bit_rate(dts_profile, dts_bit_rate):
    # If no bit rate is provided, assume the highest for Dolby Digital
    if not dts_bit_rate:
        logger.info("Stream did not contain 'bit_rate'. Setting max Dolby Digital bit rate (640k).")
        return '640k'

    # If this is DTS-HD MA, return max bit rate for Dolby Digital
    if dts_profile == 'DTS-HD MA':
        logger.info("Stream contains DTS-HD Master Audio. Setting max Dolby Digital bit rate (640k).")
        return '640k'

    # Determine bitrate based on source bitrate
    if int(dts_bit_rate) <= 768000:
        logger.info("Stream 'bit_rate' is <= 768kb/s. Setting Dolby Digital bit rate to 448k.")
        return '448k'
    elif int(dts_bit_rate) <= 1536000:
        logger.info("Stream 'bit_rate' is <= 1.5mb/s. Setting max Dolby Digital bit rate (640k).")
        return '640k'

    # Default to best quality
    logger.info("Stream 'bit_rate' could not be matched directly ({}). Setting max Dolby Digital bit rate.".format(
        dts_bit_rate))
    return '640k'


def get_stream_mapping(file_probe_streams, testing=False):
    if not file_probe_streams:
        return False

    # Map the streams into four arrays that will be placed to gether in the correct order.
    stream_mapping = []
    stream_codec = []

    video_stream_count = 0
    audio_stream_count = 0
    subtitle_stream_count = 0

    found_dts_streams = False
    for probe_stream in file_probe_streams:
        # Map the video stream
        if probe_stream.get('codec_type').lower() == "video":
            # Map this stream for copy to the destination file
            stream_mapping += ['-map', '0:v:{}'.format(video_stream_count)]
            # Add a codec flag copying this stream
            stream_codec += ['-c:v:{}'.format(video_stream_count), 'copy']
            video_stream_count += 1
            continue

        # Map the subtitle streams
        if probe_stream.get('codec_type').lower() == "subtitle":
            # Map this stream for copy to the destination file
            stream_mapping += ['-map', '0:s:{}'.format(subtitle_stream_count)]
            # Add a codec flag copying this stream
            stream_codec += ['-c:s:{}'.format(subtitle_stream_count), 'copy']
            subtitle_stream_count += 1
            continue

        # Map the audio streams
        if probe_stream.get('codec_type').lower() == "audio":
            # Check if we should clone this audio stream or convert it...
            clone_stream = True
            if probe_stream.get('codec_name').lower() == "dts":
                if should_process_dts_stream(probe_stream):
                    clone_stream = False

            if clone_stream:
                # This stream is not DTS, so only map it for copy to the destination file
                stream_mapping += ['-map', '0:a:{}'.format(audio_stream_count)]
                # Add a codec flag copying this stream
                stream_codec += ['-c:a:{}'.format(audio_stream_count), 'copy']
                audio_stream_count += 1
                continue
            else:
                # Flag this file as having a dts audio stream
                found_dts_streams = True
                if testing:
                    logger.info("File contains DTS stream that should be converted.")
                    # This is only a test to see if we should add it to the pending tasks list.
                    # Don't bother to map the streams
                    continue
                # Get the equivalent bitrate for a AC3 stream based on the bit rate of the original DTS stream
                bit_rate = get_ac3_equivalent_bit_rate(probe_stream.get('profile'), probe_stream.get('bit_rate'))
                # Map the audio stream to the destination file
                stream_mapping += ['-map', '0:a:{}'.format(audio_stream_count)]
                # Add a codec flag for encoding this stream with ac3 encoder
                stream_codec += ['-c:a:{}'.format(audio_stream_count), 'ac3', '-b:a:{}'.format(audio_stream_count),
                                 bit_rate]
                audio_stream_count += 1
                continue

    return found_dts_streams, stream_mapping, stream_codec


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
    # Get file probe
    file_probe = get_file_probe(data.get('path'))
    if not file_probe:
        # File probe failed, skip the rest of this test
        return data

    found_dts_streams, stream_mapping, stream_codec = get_stream_mapping(file_probe.get('streams'), testing=True)

    if found_dts_streams:
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug("File '{}' should be added to task list. One or more of the audio streams are DTS.".format(
            data.get('path')))

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

    # Get file probe
    file_probe = get_file_probe(data.get('file_in'))
    if not file_probe:
        # File probe failed, skip the rest of this test
        return data
    file_probe_streams = file_probe.get('streams')

    # Get stream mapping
    found_dts_streams, stream_mapping, stream_codec = get_stream_mapping(file_probe.get('streams'))

    if found_dts_streams:
        # File does not contain DTS streams
        data['exec_ffmpeg'] = True
        # Build ffmpeg args and add them to the return data
        data['ffmpeg_args'] = [
            '-i',
            data.get('file_in'),
            '-hide_banner',
            '-loglevel',
            'info',
        ]
        data['ffmpeg_args'] += stream_mapping
        data['ffmpeg_args'] += stream_codec

        # Do not remux the file. Keep the file out in the same container
        split_file_in = os.path.splitext(data.get('file_in'))
        split_file_out = os.path.splitext(data.get('file_out'))
        data['file_out'] = "{}{}".format(split_file_out[0], split_file_in[1])

        data['ffmpeg_args'] += ['-y', data.get('file_out')]

    return data
