#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     02 May 2022, (5:19 PM)

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
import hashlib
import json
import logging
import os
import stat

from unmanic.libs.unplugins.settings import PluginSettings

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.replicate_source_file_stats")


class Settings(PluginSettings):
    settings = {
        "update_mode":   True,
        "update_access": True,
        "update_modify": True,
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "update_mode":   {
                "label": "Update the destination file's mode to match that of the original source file",
            },
            "update_access": {
                "label": "Update the destination file's last access time (atime) to match that of the original source file",
            },
            "update_modify": {
                "label": "Update the destination file's last modified time (mtime) to match that of the original source file",
            },
        }


def get_file_stat(settings, path_to_file):
    """Return the file stat based on plugin config"""
    return_data = {}
    st = os.stat(path_to_file)
    if settings.get_setting('update_mode'):
        return_data['mode'] = int(st.st_mode)

    if settings.get_setting('update_access'):
        return_data['access'] = int(st.st_atime)

    if settings.get_setting('update_modify'):
        return_data['modify'] = int(st.st_mtime)

    return return_data


def on_postprocessor_file_movement(data):
    """
    Runner function - configures additional postprocessor file movements during the postprocessor stage of a task.

    The 'data' object argument includes:
        library_id              - Integer, the library that the current task is associated with.
        source_data             - Dictionary, data pertaining to the original source file.
        remove_source_file      - Boolean, should Unmanic remove the original source file after all copy operations
                                  are complete. (default: 'True' if file name has changed)
        copy_file               - Boolean, should Unmanic run a copy operation with the returned data variables.
                                  (default: 'False')
        file_in                 - String, the converted cache file to be copied by the postprocessor.
        file_out                - String, the destination file that the file will be copied to.
        run_default_file_copy   - Boolean, should Unmanic run the default post-process file movement. (default: 'True')

    :param data:
    :return:

    """
    # Configure settings object (maintain compatibility with v1 plugins)
    settings = Settings(library_id=data.get('library_id'))

    # Get the original file's absolute path
    original_source_path = data.get('source_data', {}).get('abspath')
    if not original_source_path:
        logger.error("Provided 'source_data' is missing the source file abspath data.")
        return

    # Store some required data in a JSON file for the on_postprocessor_task_results runner.
    cache_directory = os.path.dirname(data.get('file_in'))
    if not os.path.exists(cache_directory):
        os.makedirs(cache_directory)
    src_file_hash = hashlib.md5(original_source_path.encode('utf8')).hexdigest()
    plugin_data_file = os.path.join(cache_directory, '{}.json'.format(src_file_hash))
    with open(plugin_data_file, 'w') as f:
        required_data = {
            'stat': get_file_stat(settings, original_source_path),
        }
        json.dump(required_data, f, indent=4)


def on_postprocessor_task_results(data):
    """
    Runner function - provides a means for additional postprocessor functions based on the task success.

    The 'data' object argument includes:
        final_cache_path                - The path to the final cache file that was then used as the source for all destination files.
        library_id                      - The library that the current task is associated with.
        task_processing_success         - Boolean, did all task processes complete successfully.
        file_move_processes_success     - Boolean, did all postprocessor movement tasks complete successfully.
        destination_files               - List containing all file paths created by postprocessor file movements.
        source_data                     - Dictionary containing data pertaining to the original source file.

    :param data:
    :return:
    
    """
    settings = Settings(library_id=data.get('library_id'))

    # Get the original file's absolute path
    original_source_path = data.get('source_data', {}).get('abspath')
    if not original_source_path:
        logger.error("Provided 'source_data' is missing the source file abspath data.")
        return

    # Read the original file's data
    cache_directory = os.path.dirname(data.get('final_cache_path'))
    src_file_hash = hashlib.md5(original_source_path.encode('utf8')).hexdigest()
    plugin_data_file = os.path.join(cache_directory, '{}.json'.format(src_file_hash))
    if not os.path.exists(plugin_data_file):
        logger.error("Plugin data file is missing (This may be because the file movement post-processor was skipped)")
        raise Exception("Plugin data file is missing.")
    with open(plugin_data_file) as infile:
        source_file_data = json.load(infile)

    for destination_file in data.get('destination_files'):
        # Update the destination file's stats
        if not os.path.exists(destination_file):
            logger.error("Unable to find destination file '{}'".format(destination_file))
            continue

        # Update files mode
        if settings.get_setting('update_mode') and source_file_data.get('stat', {}).get('mode'):
            mode = stat.S_IMODE(int(source_file_data.get('stat', {}).get('mode')))
            try:
                os.chmod(destination_file, mode)
                logger.debug("Set the mode of destination file '{}'".format(destination_file))
            except NotImplementedError:
                logger.error("Unable to update the mode of destination file '{}'".format(destination_file))

        # Default to file's current times
        st = os.stat(destination_file)
        atime = st.st_atime
        mtime = st.st_mtime
        update = False
        if settings.get_setting('update_access') and source_file_data.get('stat', {}).get('access'):
            atime = int(source_file_data.get('stat', {}).get('access'))
            update = True
        if settings.get_setting('update_modify') and source_file_data.get('stat', {}).get('modify'):
            mtime = int(source_file_data.get('stat', {}).get('modify'))
            update = True
        if update:
            os.utime(destination_file, (atime, mtime))
            logger.debug("Set atime/mtime the of destination file '{}'".format(destination_file))

    return
