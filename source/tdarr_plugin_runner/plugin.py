#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import logging
import os
import queue
import shutil
import subprocess
import threading
import time
import zipfile
from datetime import datetime, timedelta

import requests
import uuid

from unmanic.libs.unplugins.settings import PluginSettings

from tdarr_plugin_runner.lib import tools
from tdarr_plugin_runner.lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.tdarr_plugin_runner")

community_plugin_raw_link = 'https://raw.githubusercontent.com/HaveAGitGat/Tdarr_Plugins/master/Community/{}'

plugin_root = os.path.dirname(os.path.realpath(__file__))
tdarr_plugins_path = os.path.join(plugin_root, 'Tdarr_Plugins-master')

# Set the default paths for all subprocesses
cli_tool_paths = {
    'ffmpeg':       shutil.which('ffmpeg'),
    'ffprobe':      shutil.which('ffprobe'),
    'HandBrakeCLI': shutil.which('HandBrakeCLI'),
}
with open(os.path.join(plugin_root, 'paths.json'), 'w') as f:
    json.dump(cli_tool_paths, f, indent=4)


class Settings(PluginSettings):
    settings = {
        "library_config": {},
        "global_config":  {},
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "library_config": {
                'display': 'hidden'
            },
            "global_config":  {
                'display': 'hidden'
            }
        }


def run_tdarr_plugin(plugin_id, abspath, plugin_parameters_file, plugin_results_file, worker_log):
    command_params = [
        os.path.join(plugin_root, 'scripts', 'executor.js'),
        'plugin',
        '--id', plugin_id,
        '--path', abspath,
        '--parameters', plugin_parameters_file,
        '--output', plugin_results_file,
    ]

    logger.debug("Running Tdarr plugin ID '{}'".format(plugin_id))
    result_text = tools.exec_node_cmd(command_params)
    logger.debug(result_text)
    if not os.path.exists(plugin_results_file):
        raise Exception("Results file not found after running Tdarr plugin function '{}'".format(plugin_id))
    with open(plugin_results_file) as infile:
        result_data = json.load(infile)
    if worker_log:
        worker_log.append("\n<br>{}<br>\n".format(result_data.get('data', {}).get('infoLog')))
    if result_data.get('success'):
        return result_data.get('data')
    worker_log.append("\n<br>{}<br>\n".format(result_data.get('errors')))
    logger.error(result_data.get('errors'))
    raise Exception("Failed to execute plugin function for Tdarr plugin '{}'".format(plugin_id))


def update_repo(force=False):
    # Check last installation date
    last_week = datetime.today() - timedelta(days=7)
    install_data_file = os.path.join(tdarr_plugins_path, 'install_data.json')
    try:
        with open(install_data_file) as infile:
            install_data = json.load(infile)
    except Exception as e:
        logger.warning("Unable to determine plugin install data: '{}'".format(str(e)))
    # Only update plugins once a week
    installed_date = datetime.fromisoformat(install_data.get('installed'))
    if not force and installed_date > last_week:
        return
    logger.warning("Updating plugins")
    # Download zip file
    repo_zip_url = 'https://github.com/HaveAGitGat/Tdarr_Plugins/archive/refs/heads/master.zip'
    plugins_path = os.path.join(plugin_root, 'Tdarr_Plugins-master.zip')
    tools.download_file(repo_zip_url, plugins_path)
    # Extract zip file
    with zipfile.ZipFile(plugins_path, 'r') as zip_ref:
        zip_ref.extractall(plugin_root)
    # Record installation date
    with open(install_data_file, 'w') as f:
        json.dump({'installed': str(datetime.today())}, f, indent=4)


def fetch_plugin_details(plugin_id):
    result_data = tools.fetch_plugin_details(plugin_id)
    if result_data.get('success'):
        return result_data.get('data')
    logger.error("Failed to fetch data for Tdarr plugin '{}'".format(plugin_id))
    return {}


def fetch_bulk_plugin_details(plugin_ids):
    """
    Fetch the data for one or more plugins concurrently

    :param plugin_ids:
    :return:
    """

    def threaded_task(queue1, queue2):
        """
        Threaded task to process the queue

        :param queue1:
        :param queue2:
        :return:
        """
        while not queue1.empty():
            try:
                details = fetch_plugin_details(queue1.get())
                if details:
                    queue2.put(details)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Exception in retrieving plugin ID - {}".format(str(e)))

    # Create queue of the plugin IDs that need to be processed
    plugin_ids_queue = queue.Queue()
    completed_data_queue = queue.Queue()
    for plugin_id in plugin_ids:
        plugin_ids_queue.put(plugin_id)

    # Start X threads to process plugin data fetching
    thread_list = []
    for thread_id in range(8):
        thread = threading.Thread(target=threaded_task, args=(plugin_ids_queue, completed_data_queue))
        thread_list.append(thread)
    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()

    # Extract details out of queue
    tmp_dict = {}
    while not completed_data_queue.empty():
        plugin_details = completed_data_queue.get()
        if plugin_details.get('id'):
            tmp_dict[plugin_details.get('id')] = plugin_details

    # Reorder results back into same order that the plugin_ids were provided
    plugins_list = []
    plugins_dict = {}
    for plugin_id in plugin_ids:
        plugin_data = tmp_dict.get(plugin_id, {})
        plugin_data['id'] = plugin_id
        plugins_list.append(plugin_data)
        plugins_dict[plugin_id] = plugin_data

    return plugins_list, plugins_dict


def fetch_all_plugin_details():
    plugins_path = os.path.join(tdarr_plugins_path, 'Community')

    plugin_ids = []
    for filename in os.listdir(plugins_path):
        if os.path.isfile(os.path.join(plugins_path, filename)):
            plugin_ids.append(os.path.splitext(filename)[0])

    return fetch_bulk_plugin_details(plugin_ids)


def get_library_config(library_id):
    settings = Settings(library_id=library_id)
    config = settings.get_setting('library_config')
    return {
        'installed_plugins': config.get('installed_plugins', []),
        'enabled_plugins':   config.get('enabled_plugins', []),
        'plugin_settings':   config.get('plugin_settings', {}),
    }


def set_library_config(library_id, config):
    settings = Settings(library_id=library_id)
    return settings.set_setting('library_config', config)


def get_global_config(library_id):
    settings = Settings(library_id=library_id)
    config = settings.get_setting('global_config')
    if not config:
        config = {}
    return config


def set_global_config(library_id, config):
    settings = Settings(library_id=library_id)
    return settings.set_setting('global_config', config)


def request_get_tdarr_repo(data):
    arguments = data.get('arguments', {})
    force_update = False
    if arguments.get('force_update') and str(arguments.get('force_update')[0].decode("utf-8")) == 'true':
        force_update = True

    update_repo(force_update)

    plugins_list, plugins_dict = fetch_all_plugin_details()
    return {
        'success': True,
        'data':    plugins_list,
    }


def request_get_plugin_details(data):
    arguments = data.get('arguments', {})
    plugin_id = arguments.get('plugin_id')
    if plugin_id:
        plugin_id = str(plugin_id[0].decode("utf-8"))

    if plugin_id:
        return fetch_plugin_details(plugin_id)
    return []


def request_install_plugin_to_library(data):
    arguments = data.get('arguments', {})
    plugin_id = arguments.get('plugin_id')
    if plugin_id:
        plugin_id = str(plugin_id[0].decode("utf-8"))
    library_id = arguments.get('library_id')
    if library_id:
        library_id = str(library_id[0].decode("utf-8"))
    library_config = get_library_config(library_id)

    # Check that it is not already installed
    already_installed = False
    if not library_config.get('installed_plugins'):
        library_config['installed_plugins'] = []
    for installed_plugin in library_config['installed_plugins']:
        if installed_plugin == plugin_id:
            already_installed = True
            break
    if not already_installed:
        library_config['installed_plugins'].append(plugin_id)

    # Save config
    if set_library_config(library_id, library_config):
        return {'success': True}
    return {'success': False}


def request_remove_plugin_from_library(data):
    arguments = data.get('arguments', {})
    plugin_id = arguments.get('plugin_id')
    if plugin_id:
        plugin_id = str(plugin_id[0].decode("utf-8"))
    library_id = arguments.get('library_id')
    if library_id:
        library_id = str(library_id[0].decode("utf-8"))
    library_config = get_library_config(library_id)

    # Loop over currently installed plugins and re-add to the new list all that do not match the given ID
    new_plugin_list = []
    for installed_plugin in library_config.get('installed_plugins', []):
        if installed_plugin != plugin_id:
            new_plugin_list.append(installed_plugin)

    # Update the installed_plugins value with the new list
    library_config['installed_plugins'] = new_plugin_list

    # Save config
    if set_library_config(library_id, library_config):
        return {'success': True}
    return {'success': False}


def request_enable_plugin_to_library(data):
    arguments = data.get('arguments', {})
    plugin_id = arguments.get('plugin_id')
    if plugin_id:
        plugin_id = str(plugin_id[0].decode("utf-8"))
    library_id = arguments.get('library_id')
    if library_id:
        library_id = str(library_id[0].decode("utf-8"))
    library_config = get_library_config(library_id)

    # Check that it is not already installed
    already_installed = False
    if not library_config.get('enabled_plugins'):
        library_config['enabled_plugins'] = []
    for installed_plugin in library_config['enabled_plugins']:
        if installed_plugin == plugin_id:
            already_installed = True
            break
    if not already_installed:
        library_config['enabled_plugins'].append(plugin_id)

    # Save config
    if set_library_config(library_id, library_config):
        return {'success': True}
    return {'success': False}


def request_disable_plugin_from_library(data):
    arguments = data.get('arguments', {})
    plugin_id = arguments.get('plugin_id')
    if plugin_id:
        plugin_id = str(plugin_id[0].decode("utf-8"))
    library_id = arguments.get('library_id')
    if library_id:
        library_id = str(library_id[0].decode("utf-8"))
    library_config = get_library_config(library_id)

    # Loop over currently installed plugins and re-add to the new list all that do not match the given ID
    new_plugin_list = []
    for installed_plugin in library_config.get('enabled_plugins', []):
        if installed_plugin != plugin_id:
            new_plugin_list.append(installed_plugin)

    # Update the enabled_plugins value with the new list
    library_config['enabled_plugins'] = new_plugin_list

    # Save config
    if set_library_config(library_id, library_config):
        return {'success': True}
    return {'success': False}


def request_get_library_config(data):
    arguments = data.get('arguments', {})
    library_id = arguments.get('library_id')
    if library_id:
        library_id = str(library_id[0].decode("utf-8"))

    # Fetch config
    library_config = get_library_config(library_id)
    if not library_config:
        return {'success': False}

    # Fetch details for all installed plugins
    installed_plugin_ids = library_config.get('installed_plugins', [])
    plugin_details = {}
    if installed_plugin_ids:
        plugins_list, plugins_dict = fetch_bulk_plugin_details(installed_plugin_ids)
        if not plugins_dict:
            return {'success': False}
        plugin_details = plugins_dict

    return {
        'success': True,
        'data':    {
            'config':         library_config,
            'plugin_details': plugin_details,
        },
    }


def request_set_library_plugin_config(data):
    arguments = data.get('arguments', {})
    library_id = arguments.get('library_id')
    if library_id:
        library_id = str(library_id[0].decode("utf-8"))
    encoded_data = arguments.get('data')
    if encoded_data:
        encoded_data = str(encoded_data[0].decode("utf-8"))

    # Decode JSON
    decoded_data = base64.b64decode(encoded_data)
    config = json.loads(decoded_data)

    # Read the library config
    library_config = get_library_config(library_id)

    # Update the library config with the new plugin order
    if config.get('installed_plugins'):
        if not library_config.get('installed_plugins'):
            library_config['installed_plugins'] = []
        library_config['installed_plugins'] = config.get('installed_plugins')

    # Update the library config with the new plugin settings
    if config.get('plugin_settings'):
        if not library_config.get('plugin_settings'):
            library_config['plugin_settings'] = {}
        library_config['plugin_settings'] = config.get('plugin_settings')

    # Save config
    if set_library_config(library_id, library_config):
        return {
            'success': True,
        }

    return {'success': False}


def request_get_global_config(data):
    arguments = data.get('arguments', {})
    library_id = arguments.get('library_id')
    if library_id:
        library_id = str(library_id[0].decode("utf-8"))

    # Fetch config
    global_config = get_global_config(library_id)
    success = True
    if not global_config:
        success = False

    return {
        'success': success,
        'data':    {
            'global_config': global_config,
        },
    }


def request_set_global_config(data):
    arguments = data.get('arguments', {})
    library_id = arguments.get('library_id')
    if library_id:
        library_id = str(library_id[0].decode("utf-8"))

    # Read the library config
    global_config = get_global_config(library_id)

    for gc in arguments:
        if gc == 'library_id':
            continue
        value = str(arguments[gc][0].decode("utf-8"))
        global_config[gc] = value

    # Save config
    if set_global_config(library_id, global_config):
        return {
            'success': True,
        }

    return {'success': False}


def select_plugin(settings, status):
    selected_plugin = None
    library_config = settings.get_setting('library_config')
    installed_plugins = library_config.get('installed_plugins', [])
    enabled_plugins = library_config.get('enabled_plugins', [])

    # Loop over installed plugins in order (as this is the order of priority)
    select_next_plugin = False
    for plugin in installed_plugins:
        # Ignore disabled plugins
        if plugin not in enabled_plugins:
            continue
        # If the status has no previous_plugin set, then this is possibly the first run.
        # Set the selected plugin as the first one in this list
        if status.get('previous_plugin') is None:
            selected_plugin = plugin
            break
        # This is the next plugin in the list that is flagged to be executed by the following logic, select it
        if select_next_plugin:
            selected_plugin = plugin
            break
        # If this plugin did not request to process the file in the previous run, select the next plugin
        if plugin == status.get('previous_plugin') and not status.get('process_file'):
            select_next_plugin = True
            continue
        # If this plugin did request to process the file and plugin previously requested a re-run, reselect it again
        if plugin == status.get('previous_plugin') and status.get('requeue_after'):
            selected_plugin = plugin
            break

    return selected_plugin


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

    # Get settings
    settings = Settings(library_id=data.get('library_id'))

    # Get the path to the file
    abspath = data.get('file_in')

    # Set a hash unique to this task
    src_file_hash = hashlib.md5(data.get('original_file_path').encode('utf8')).hexdigest()

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video', 'audio'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return
    original_file_probe = Probe(logger, allowed_mimetypes=['video', 'audio'])
    original_file_probe.file(data.get('original_file_path'))

    # Ensure cache directory exists
    cache_directory = os.path.dirname(data.get('file_out'))
    if not os.path.exists(cache_directory):
        os.makedirs(cache_directory)

    # Read status file
    plugin_status_file = os.path.join(cache_directory, '{}-status.json'.format(src_file_hash))
    status = {}
    if os.path.exists(plugin_status_file):
        with open(plugin_status_file) as infile:
            status = json.load(infile)

    # Get plugin ID to run on this iteration
    plugin_id = select_plugin(settings, status)
    if plugin_id is None:
        # No plugins are configured to run
        return
    if data.get('worker_log'):
        data['worker_log'].append("\nRunning Tdarr plugin ID: '<em>{}</em>'".format(plugin_id))

    # Ensure all jobs are carried out in the cache
    # Tdarr replaces the source file after each process. We need to simulate that here
    cache_directory = os.path.dirname(data.get('file_out'))
    if not os.path.exists(cache_directory):
        os.makedirs(cache_directory)
    # Generate the new temp cache file
    extension = os.path.splitext(data.get('file_in'))[1]
    original_file_basename = os.path.basename(data.get('original_file_path'))
    # temp_path = os.path.join(cache_directory, original_file_basename)
    temp_path = tools.update_output_file_path(os.path.join(cache_directory, original_file_basename), extension)
    # If this the first plugin, copy the source file to the cache, otherwise move it
    if data.get('file_in') == data.get('original_file_path'):
        shutil.copyfile(data.get('file_in'), temp_path)
    elif data.get('file_in') != temp_path:
        shutil.move(data.get('file_in'), temp_path)
    # Set the file_in to the new temp path
    data['file_in'] = temp_path
    # Reset probe with new file in
    probe.file(data.get('file_in'))

    # Set library settings paths
    cache_directory = os.path.dirname(data.get('file_out'))
    library_settings = tools.get_library_settings_params(settings, cache_directory, data.get('original_file_path'))

    # Configure plugin params dictionary
    plugin_parameters = {
        'file':            tools.get_file_params(settings, data.get('file_in'), probe),
        'librarySettings': library_settings,
        'inputs':          tools.get_plugin_inputs(settings, plugin_id),
        'otherArguments':  {
            'handbrakePath':       cli_tool_paths.get('HandBrakeCLI'),
            'ffmpegPath':          cli_tool_paths.get('ffmpeg'),
            'originalLibraryFile': tools.get_file_params(settings, data.get('original_file_path'), original_file_probe),
        },
    }

    # Create params file for these args. Dump them there for the executor to read
    plugin_parameters_file = os.path.join(cache_directory, '{}-parameters.json'.format(src_file_hash))
    with open(plugin_parameters_file, 'w') as param_file:
        json.dump(plugin_parameters, param_file, indent=4)

    # Execute configured Tdarr plugin by the ID.
    plugin_results_file = os.path.join(cache_directory, '{}-results.json'.format(src_file_hash))
    result = run_tdarr_plugin(plugin_id, abspath, plugin_parameters_file, plugin_results_file, data.get('worker_log'))

    # Update status
    status['previous_plugin'] = plugin_id
    status['requeue_after'] = result.get('reQueueAfter')
    status['process_file'] = result.get('processFile')

    # Re-run this plugin if the plugin set the 'reQueueAfter' flag
    if result.get('reQueueAfter'):
        data['repeat'] = True

    # Update output file with plugin specified container
    extension = result.get('container', '')
    data['file_out'] = tools.update_output_file_path(data['file_out'], extension)

    # Generate command
    if result.get('processFile') and result.get('FFmpegMode'):
        data['exec_command'] = tools.generate_ffmpeg_command(data['file_in'], data['file_out'], result)

    # Create/update status file for subsequent runs of the plugin to read
    with open(plugin_status_file, 'w') as status_file:
        json.dump(status, status_file, indent=4)


def render_frontend_panel(data):
    """
    Runner function - display a custom data panel in the frontend.

    The 'data' object argument includes:
        content_type                    - The content type to be set when writing back to the browser.
        content                         - The content to print to the browser.
        path                            - The path received after the '/unmanic/panel' path.
        arguments                       - A dictionary of GET arguments received.

    :param data:
    :return:
    
    """
    # API
    if data.get('path') in ['tdarr_repo', '/tdarr_repo', '/tdarr_repo/']:
        data['content_type'] = 'application/json'
        data['content'] = request_get_tdarr_repo(data)
        return

    if data.get('path') in ['plugin_details', '/plugin_details', '/plugin_details/']:
        data['content_type'] = 'application/json'
        data['content'] = request_get_plugin_details(data)
        return

    if data.get('path') in ['install', '/install', '/install/']:
        data['content_type'] = 'application/json'
        data['content'] = request_install_plugin_to_library(data)
        return

    if data.get('path') in ['remove', '/remove', '/remove/']:
        data['content_type'] = 'application/json'
        data['content'] = request_remove_plugin_from_library(data)
        return

    if data.get('path') in ['enable', '/enable', '/enable/']:
        data['content_type'] = 'application/json'
        data['content'] = request_enable_plugin_to_library(data)
        return

    if data.get('path') in ['disable', '/disable', '/disable/']:
        data['content_type'] = 'application/json'
        data['content'] = request_disable_plugin_from_library(data)
        return

    if data.get('path') in ['get_config', '/get_config', '/get_config/']:
        data['content_type'] = 'application/json'
        data['content'] = request_get_library_config(data)
        return

    if data.get('path') in ['/set_plugin_config']:
        data['content_type'] = 'application/json'
        data['content'] = request_set_library_plugin_config(data)
        return

    if data.get('path') in ['get_global_config', '/get_global_config', '/get_global_config/']:
        data['content_type'] = 'application/json'
        data['content'] = request_get_global_config(data)
        return

    # Pages
    if data.get('path') in ['/page_options']:
        if data.get('arguments'):
            request_set_global_config(data)

        with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'config.html'))) as f:
            content = f.read()
            data['content'] = content.replace("{cache_buster}", str(uuid.uuid4()))
        return

    if data.get('path') in ['/page_libraries']:
        with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'index.html'))) as f:
            content = f.read()
            data['content'] = content.replace("{cache_buster}", str(uuid.uuid4()))
        return

    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'index.html'))) as f:
        content = f.read()
        data['content'] = content.replace("{cache_buster}", str(uuid.uuid4()))

    return
