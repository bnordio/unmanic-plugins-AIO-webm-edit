#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic-plugins.plugin.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     01 Jul 2021, (12:22 PM)

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
logger = logging.getLogger("Unmanic.Plugin.normalise_aac")


class Settings(PluginSettings):
    settings = {
        'I':                           '-24.0',
        'LRA':                         '7.0',
        'TP':                          '-2.0',
        'ignore_previously_processed': True,
    }
    form_settings = {
        "I":                           {
            "label": "The integrated loudness target. Range is '-70.0' to '-5.0'. Default value is '-24.0'.",
        },
        "LRA":                         {
            "label": "Loudness range. Range is '1.0' to '20.0'. Default value is '7.0'. ",
        },
        "TP":                          {
            "label": "The maximum true peak. Range is '-9.0' to '+0.0'. Default value is '-2.0'. ",
        },
        "ignore_previously_processed": {
            "label": "Ignore all files previously normalised with this plugin regardless of the settings above.",
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


def audio_filtergraph():
    settings = Settings()
    i = settings.get_setting('I')
    if not i:
        i = settings.settings.get('I')
    lra = settings.get_setting('LRA')
    if not lra:
        i = settings.settings.get('LRA')
    tp = settings.get_setting('TP')
    if not tp:
        i = settings.settings.get('TP')

    return 'loudnorm=I={}:LRA={}:TP={}'.format(i, lra, tp)


def stream_normalised(probe_stream):
    settings = Settings()

    stream_tags = probe_stream.get('tags')
    if 'unmanic:normalise_aac' in probe_stream.get('tags'):
        # This stream already has been normalised
        if settings.get_setting('ignore_previously_processed'):
            return True
        elif stream_tags.get('unmanic:normalise_aac') == audio_filtergraph():
            # The previously normalised stream matches what is already confiured
            return True
        else:
            logger.debug(
                "File's stream was previously normalised with {}.".format(stream_tags.get('unmanic:normalise_aac')))

    # Default to
    return False


def get_stream_mapping(file_probe_streams, testing=False):
    if not file_probe_streams:
        return False

    # Map the streams into four arrays that will be placed to gether in the correct order.
    stream_mapping = []
    stream_codec = []

    video_stream_count = 0
    audio_stream_count = 0
    subtitle_stream_count = 0

    found_aac_streams_to_normalise = False
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
            # Check if we should just copy this audio stream or convert it...
            copy_stream = True
            if probe_stream.get('codec_name').lower() == "aac":
                if not stream_normalised(probe_stream):
                    copy_stream = False

            if copy_stream:
                # This stream is not AAC or is already normalised, so only map it for copy to the destination file
                stream_mapping += ['-map', '0:a:{}'.format(audio_stream_count)]
                # Add a codec flag copying this stream
                stream_codec += ['-c:a:{}'.format(audio_stream_count), 'copy']
                audio_stream_count += 1
                continue
            else:
                # Flag this file as having an aac audio stream that needs to be normalised
                found_aac_streams_to_normalise = True
                if testing:
                    logger.info("File contains AAC stream that should be normalised.")
                    # This is only a test to see if we should add it to the pending tasks list.
                    # Don't bother to map the streams
                    continue
                # Map the audio stream to the destination file
                stream_mapping += ['-map', '0:a:{}'.format(audio_stream_count)]
                # Add a codec flag for encoding this stream with ac3 encoder
                stream_codec += [
                    '-c:a:{}'.format(audio_stream_count), 'aac',
                    '-filter:a:{}'.format(audio_stream_count), audio_filtergraph(),
                    '-metadata:s:a:{}'.format(audio_stream_count),
                    "unmanic:normalise_aac='{}'".format(audio_filtergraph()),

                ]
                audio_stream_count += 1
                continue

    return found_aac_streams_to_normalise, stream_mapping, stream_codec


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

    found_streams, stream_mapping, stream_codec = get_stream_mapping(file_probe.get('streams'), testing=True)

    if found_streams:
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug(
            "File '{}' should be added to task list. One or more of the audio streams should be normalised.".format(
                data.get('path'))
        )
    else:
        logger.debug("File '{}' does not contain audio streams needing to be normalised.".format(
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
    found_streams, stream_mapping, stream_codec = get_stream_mapping(file_probe.get('streams'))

    if found_streams:
        # File has streams to normalise
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
