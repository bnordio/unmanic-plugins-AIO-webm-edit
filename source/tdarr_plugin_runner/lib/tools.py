#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.tools.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Apr 2022, (7:06 PM)

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
import os
import re
import shutil
import subprocess
import time

import exiftool
import requests

tdarr_parameters = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tdarr_parameters')


def exec_node_cmd(params):
    command = ["node"] + params

    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = pipe.communicate()

    # Check for results
    try:
        raw_output = out.decode("utf-8")
    except Exception as e:
        raise Exception("Unable to decode output from command {}. {}".format(command, str(e)))
    if pipe.returncode != 0:
        raise Exception("Plugin did not execute correctly. '{}'".format(' '.join(command)))

    return raw_output


def exec_mpx_cmd(params):
    plugin_root = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
    command = ["npx"] + params

    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=plugin_root)
    out, err = pipe.communicate()

    # Check for results
    try:
        raw_output = out.decode("utf-8")
    except Exception as e:
        raise Exception("Unable to decode output from command {}. {}".format(command, str(e)))
    if pipe.returncode != 0:
        raise Exception("Plugin did not execute correctly. '{}'".format(' '.join(command)))

    return raw_output


def download_file(url, path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    f.write(chunk)


def fetch_plugin_details(plugin_id):
    plugin_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    tdarr_plugins_path = os.path.join(plugin_root, 'Tdarr_Plugins-master')
    plugins_path = os.path.join(tdarr_plugins_path, 'Community')

    # Ensure we have a local copy of the plugin
    plugin_file = os.path.join(plugins_path, "{}.js".format(plugin_id))
    if not os.path.exists(plugin_file):
        raise Exception("Plugin does not exist '{}'".format(plugin_id))

    command_params = [
        os.path.join(plugin_root, 'lib', 'executor.js'),
        'details',
        '--id', plugin_id,
    ]
    result_text = exec_node_cmd(command_params)
    return json.loads(result_text)


def fetch_exiftool_data(abspath):
    if shutil.which('exiftool') is None:
        raise Exception("Unable to find executable 'exiftool'. Please ensure that exiftool is installed correctly.")
    with exiftool.ExifTool(common_args=['-n']) as et:
        metadata = et.get_metadata(abspath)
    return metadata


def fetch_mediainfo_data(abspath):
    command_params = [
        'mediainfo.js',
        abspath,
        '--format', 'JSON',
    ]
    result_text = exec_mpx_cmd(command_params)
    result_data = json.loads(result_text)
    if result_data.get('media'):
        return result_data.get('media')
    return {}


def calculate_video_resolution(settings, vid_width, vid_height):
    global_config = settings.get_setting('global_config')
    # parse resBoundaries
    res_boundaries = {
        '480p':  {
            'widthMin':  global_config.get('res480p,widthMin', '100'),
            'widthMax':  global_config.get('res480p,widthMax', '793'),
            'heightMin': global_config.get('res480p,heightMin', '100'),
            'heightMax': global_config.get('res480p,heightMax', '528'),
        },
        '576p':  {
            'widthMin':  global_config.get('res576p,widthMin', '100'),
            'widthMax':  global_config.get('res576p,widthMax', '792'),
            'heightMin': global_config.get('res576p,heightMin', '100'),
            'heightMax': global_config.get('res576p,heightMax', '634'),
        },
        '720p':  {
            'widthMin':  global_config.get('res720p,widthMin', '100'),
            'widthMax':  global_config.get('res720p,widthMax', '1408'),
            'heightMin': global_config.get('res720p,heightMin', '100'),
            'heightMax': global_config.get('res720p,heightMax', '792'),
        },
        '1080p': {
            'widthMin':  global_config.get('res1080p,widthMin', '100'),
            'widthMax':  global_config.get('res1080p,widthMax', '2112'),
            'heightMin': global_config.get('res1080p,heightMin', '100'),
            'heightMax': global_config.get('res1080p,heightMax', '1188'),
        },
        '4KUHD': {
            'widthMin':  global_config.get('res4KUHD,widthMin', '100'),
            'widthMax':  global_config.get('res4KUHD,widthMax', '4224'),
            'heightMin': global_config.get('res4KUHD,heightMin', '100'),
            'heightMax': global_config.get('res4KUHD,heightMax', '2376'),
        },
        'DCI4K': {
            'widthMin':  global_config.get('resDCI4K,widthMin', '100'),
            'widthMax':  global_config.get('resDCI4K,widthMax', '4506'),
            'heightMin': global_config.get('resDCI4K,heightMin', '100'),
            'heightMax': global_config.get('resDCI4K,heightMax', '2376'),
        },
        '8KUHD': {
            'widthMin':  global_config.get('res8KUHD,widthMin', '100'),
            'widthMax':  global_config.get('res8KUHD,widthMax', '8448'),
            'heightMin': global_config.get('res8KUHD,heightMin', '100'),
            'heightMax': global_config.get('res8KUHD,heightMax', '5752'),
        },
    }

    def check_res_within_boundaries(option):
        if int(vid_width) < int(res_boundaries[option]['widthMin']):
            return False
        if int(vid_width) > int(res_boundaries[option]['widthMax']):
            return False
        if int(vid_height) < int(res_boundaries[option]['heightMin']):
            return False
        if int(vid_height) > int(res_boundaries[option]['heightMax']):
            return False
        return True

    video_resolution = 'Other'
    for res in res_boundaries:
        if check_res_within_boundaries(res):
            video_resolution = res
            break
    return video_resolution


def get_video_stream_data(streams):
    width = 0
    height = 0
    video_stream_index = 0

    for stream in streams:
        if stream.get('codec_type') == 'video':
            width = stream.get('width', stream.get('coded_width', 0))
            height = stream.get('height', stream.get('coded_height', 0))
            video_stream_index = stream.get('index')
            break

    return width, height, video_stream_index


def check_file_medium(streams):
    has_video = False
    has_audio = False
    has_subtitles = False
    video_codec_name = ''
    audio_codec_name = ''

    for stream in reversed(streams):
        if stream.get('codec_type') == 'video':
            has_video = True
            video_codec_name = stream.get('codec_name')
        elif stream.get('codec_type') == 'audio':
            has_audio = True
            audio_codec_name = stream.get('codec_name')
        elif stream.get('codec_type') == 'subtitle':
            has_subtitles = True

    file_medium = 'other'
    if has_video:
        file_medium = 'video'
    elif has_audio:
        file_medium = 'audio'
    return file_medium, video_codec_name, audio_codec_name, has_subtitles


def get_bit_rate(abspath, exiftool_data, probe):
    source_size = os.path.getsize(abspath)
    if exiftool_data.get('Durations'):
        return (8 * source_size) / float(exiftool_data.get('Duration'))
    elif probe.get('format', {}).get('duration'):
        return (8 * source_size) / float(probe.get('format', {}).get('duration'))


def get_file_extension(file_path):
    split_file_in = os.path.splitext(file_path)
    return split_file_in[1].lstrip('.')


def get_file_params(settings, abspath, probe):
    template = os.path.join(tdarr_parameters, 'file.json')
    template_data = {}
    try:
        with open(template) as infile:
            template_data = json.load(infile)
    except Exception as e:
        pass

    # Fetch exiftool data
    exiftool_data = fetch_exiftool_data(abspath)

    # Fetch mediainfo data
    mediainfo_data = fetch_mediainfo_data(abspath)

    # Get file extension
    file_extension = get_file_extension(abspath)

    # Get video width and height and the index of the video stream
    vid_width, vid_height, video_stream_index = get_video_stream_data(probe.get('streams', []))

    # Check if file is video, audio or other and get codec
    file_medium, video_codec_name, audio_codec_name, has_subtitles = check_file_medium(probe.get('streams'))

    # Get video bitrate
    bit_rate = get_bit_rate(abspath, exiftool_data, probe)

    # Update template. Holy shit what a waste of time this all is.
    # Whoever wrote the original Tdarr file meta collection was an idiot!
    # So much duplication of effort. So much useless, untidy code.
    # TODO: These dont seem to be used, so I cant be bothered adding them
    #  lastPluginDetails
    #  processingStatus
    #  statSync
    #  tPosition
    #  hPosition
    data = {
        '_id':                    abspath,
        'file':                   abspath,
        'hasClosedCaptions':      has_subtitles,
        'container':              file_extension,
        'ffProbeData':            {
            'streams': probe.get('streams'),
        },
        'file_size':              probe.get('format', {}).get('size'),
        'video_resolution':       calculate_video_resolution(settings, vid_width, vid_height),
        'fileMedium':             file_medium,
        'video_codec_name':       video_codec_name,
        'audio_codec_name':       audio_codec_name,
        'lastPluginDetails':      "none",
        'processingStatus':       False,
        'createdAt':              time.time(),
        'bit_rate':               bit_rate,
        'statSync':               {},
        'HealthCheck':            "",
        'TranscodeDecisionMaker': "",
        'lastHealthCheckDate':    0,
        'holdUntil':              0,
        'lastTranscodeDate':      0,
        'infoLog':                "",
        'bumped':                 False,
        'history':                "",
        'oldSize':                0,
        'newSize':                0,
        'videoStreamIndex':       video_stream_index,
        'meta':                   exiftool_data,
        'mediaInfo':              mediainfo_data,
        'tPosition':              0,
        'hPosition':              0,
    }

    return {**template_data, **data}


def get_library_settings_params(settings, cache_directory, original_file_path):
    source_directory = os.path.dirname(original_file_path)
    # Get container filter from settings
    global_config = settings.get_setting('global_config')
    container_filter = global_config.get('containerFilter',
                                         'mkv,mp4,mov,m4v,mpg,mpeg,avi,flv,webm,wmv,vob,evo,iso,m2ts,ts')
    file_extension = get_file_extension(original_file_path)
    return {
        'name':                                 'Test',
        'priority':                             0,
        'folder':                               source_directory,
        'cache':                                cache_directory,
        'output':                               cache_directory,
        'folderToFolderConversion':             False,
        'folderToFolderConversionDeleteSource': False,
        'copyIfConditionsMet':                  False,
        'container':                            '.{}'.format(file_extension),
        'containerFilter':                      container_filter,
        'createdAt':                            time.time(),
        'folderWatching':                       False,
        'useFsEvents':                          False,
        'scheduledScanFindNew':                 False,
        'processLibrary':                       True,
        'scanOnStart':                          False,
        'exifToolScan':                         True,
        'mediaInfoScan':                        True,
        'closedCaptionScan':                    False,
        'scanButtons':                          True,
        'scanFound':                            'Files found:1',
        'expanded':                             True,
        'navItemSelected':                      'navSourceFolder',
        'pluginCommunity':                      False,
        'handbrake':                            True,
        'ffmpeg':                               False,
        'handbrakescan':                        True,
        'ffmpegscan':                           False,
    }


def get_plugin_inputs(settings, plugin_id):
    library_config = settings.get_setting('library_config')
    plugin_input_config = library_config.get('plugin_settings', {}).get(plugin_id, {})
    # Fetch plugin inputs from details
    plugin_inputs = {}
    result_data = fetch_plugin_details(plugin_id)
    if result_data.get('success'):
        for i in result_data.get('data', {}).get('Inputs', []):
            input_name = i.get('name')
            input_value = i.get('defaultValue')
            if plugin_input_config.get(input_name):
                # Override the default value with the configured value
                input_value = plugin_input_config.get(input_name)
            plugin_inputs[input_name] = input_value
    return plugin_inputs


def update_output_file_path(out_file, extension):
    split_out_file = os.path.splitext(out_file)
    return "{}.{}".format(split_out_file[0], extension.lstrip('.'))


def generate_ffmpeg_command(in_file, out_file, params):
    preset = params.get('preset', '')
    # preset = '<io>-af ' + "'loudnorm=I=-23.0:LRA=7.0:TP=-2.0:print_format=json'" + ' -f null NUL -map 0 -c copy -metadata NORMALISATIONSTAGE="FirstPassComplete" 2>"/library/TEST_FILE.out"'
    if '<io>' in preset:
        presetSplit = preset.split("<io>")
    else:
        presetSplit = preset.split(",")

    preset0 = re.sub(r"'", "'\"'\"'", presetSplit[0])
    preset1 = re.sub(r"'", "'\"'\"'", presetSplit[1])

    return "ffmpeg " + preset0 + " -i '" + in_file + "' " + preset1 + " '" + out_file + "' "
