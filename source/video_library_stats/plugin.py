#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     28 Nov 2021, (3:27 PM)

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
import os
import threading
import uuid
import datetime

from peewee import *
from playhouse.shortcuts import model_to_dict
from playhouse.sqliteq import SqliteQueueDatabase
from unmanic.libs.singleton import SingletonType

from unmanic.libs.unplugins.settings import PluginSettings

from video_library_stats.lib.ffmpeg import Probe

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.video_library_stats")


class Settings(PluginSettings):
    settings = {}


settings = Settings()
profile_directory = settings.get_profile_directory()
db_file = os.path.abspath(os.path.join(profile_directory, 'library_stats.db'))
db = SqliteQueueDatabase(
    db_file,
    use_gevent=False,
    autostart=True,
    queue_max_size=None,
    results_timeout=15.0,
)


class BaseModel(Model):
    """
    BaseModel

    Generic configuration and methods used across all Model classes
    """

    class Meta:
        database = db

    def model_to_dict(self):
        """
        Retrieve all related objects recursively and
        then converts the resulting objects to a dictionary.

        :return:
        """
        return model_to_dict(self, backrefs=True)


class VideoFile(BaseModel):
    """
    HistoricTasks
    """
    abspath = TextField(null=False, default='UNKNOWN', unique=True)
    last_tested = DateTimeField(null=False, default=datetime.datetime.now)
    basename = TextField(null=False, default='UNKNOWN')
    container_name = TextField(null=False, default='UNKNOWN')
    video_codec = TextField(null=False, default='UNKNOWN')
    video_width = IntegerField(null=True)
    video_height = IntegerField(null=True)


class Data(object):

    def __init__(self):
        self.create_db_schema()

    def create_db_schema(self):
        # Create required tables in new DB
        logger.debug("Ensuring video file stats database schema exists")
        db.create_tables([VideoFile], safe=True)

    def fetch_outdated_file_paths(self):
        """
        Fetch all entries that are more than a day old

        :return:
        """
        today = datetime.date.today()
        an_hour_ago = today - datetime.timedelta(minutes=60)
        return VideoFile.select().where(VideoFile.last_tested < an_hour_ago)

    def fetch_all_video_file_data(self, path_filter=None):
        """
        Fetch all entries that are more than a day old

        :return:
        """
        query = VideoFile.select(VideoFile.abspath,
                                 VideoFile.basename,
                                 VideoFile.container_name,
                                 VideoFile.video_codec,
                                 VideoFile.video_width,
                                 VideoFile.video_height)
        if path_filter:
            query = query.where(VideoFile.abspath.contains(path_filter))
        return query

    def get_container_names(self, path_filter=None):
        """
        SELECT
			container_name,
			COUNT ( id ) AS "count"
        FROM
			videofile
        GROUP BY container_name
        ;

        :return:
        """
        query = VideoFile.select(VideoFile.container_name, fn.Count(VideoFile.id).alias('count'))
        if path_filter:
            query = query.where(VideoFile.abspath.contains(path_filter))
        query = query.group_by(VideoFile.container_name)
        results = query.dicts()
        return list(results)

    def get_video_codecs(self, path_filter=None):
        """
        SELECT
			video_codec,
			COUNT ( id ) AS "count"
        FROM
			videofile
        GROUP BY video_codec
        ;

        :return:
        """
        query = VideoFile.select(VideoFile.video_codec, fn.Count(VideoFile.id).alias('count'))
        if path_filter:
            query = query.where(VideoFile.abspath.contains(path_filter))
        query = query.group_by(VideoFile.video_codec)
        results = query.dicts()
        return list(results)

    def get_video_resolutions(self, path_filter=None):
        """
        SELECT
			video_width || 'x' || video_height as "resolution",
			COUNT(id) AS "count"
        FROM
			videofile
		WHERE
			video_width IS NOT NULL
			AND
			video_height IS NOT NULL
        GROUP BY (video_width || 'x' || video_height)
        ;

        :return:
        """
        resolution = VideoFile.video_width.concat('x').concat(VideoFile.video_height)
        query = VideoFile.select(resolution.alias('resolution'), fn.Count(VideoFile.id).alias('count'))
        query = query.where(VideoFile.video_width.is_null(False) & VideoFile.video_height.is_null(False))
        if path_filter:
            query = query.where(VideoFile.abspath.contains(path_filter))
        query = query.group_by(resolution)
        query = query.order_by(VideoFile.video_width)
        results = query.dicts()
        return list(results)

    def get_top_10_paths(self, path_filter=None):
        """
        SELECT
			abspath,
        FROM
			videofile
        LIMIT 10
        ;

        :return:
        """
        query = VideoFile.select(VideoFile.abspath)
        if path_filter:
            query = query.where(VideoFile.abspath.contains(path_filter))
        # query = query.where(VideoFile.abspath.is_null(False))
        # query = query.where(VideoFile.abspath != '')
        query = query.limit(10)
        results = query.dicts()
        return list(results)

    def save_video_file_item(self, abspath: str, container_name: str, video_codec: str, video_width,
                             video_height):
        try:
            # First try to add the abs path
            VideoFile.create(
                abspath=abspath,
                basename=os.path.basename(abspath),
                container_name=container_name,
                video_codec=video_codec,
                video_width=video_width,
                video_height=video_height,
            )
        except IntegrityError:
            video_file = VideoFile.select().where(VideoFile.abspath == abspath).limit(1).get()
            video_file.last_tested = datetime.datetime.now()
            video_file.basename = os.path.basename(abspath)
            video_file.container_name = container_name
            video_file.video_codec = video_codec
            video_file.video_width = video_width
            video_file.video_height = video_height
            video_file.save()
            return True
        except Exception:
            logger.exception("Failed to save video metrics for file: '{}'".format(abspath))
            return False


class DataCleanup(object, metaclass=SingletonType):
    last_run = None

    def test_outdated_files_still_exist(self):
        """
        Check database for any outdated files
        If there are any, ensure that these files still exist on disk
        If they do not exist on disk, remove them

        :return:
        """
        lock = threading.RLock()
        lock.acquire()

        # Only run this check once a min
        # This prevents multiple threads from running it before the SqliteQueueDatabase can commit any deletes
        x_min_ago = datetime.datetime.now() - datetime.timedelta(minutes=1)
        if self.last_run is None:
            self.last_run = x_min_ago
        if self.last_run > x_min_ago:
            lock.release()
            return

        # Fetch items that are more than a day old since last checked
        db_data = Data()
        # outdated_file_paths = db_data.fetch_outdated_file_paths()
        all_file_paths = db_data.fetch_all_video_file_data()

        # Loop over these items and ensure that their paths still exist on disk
        for item in all_file_paths:
            abspath = os.path.abspath(item.abspath)
            if not os.path.exists(abspath):
                # This item does not exist any longer, remove it from the database
                logger.info("Removing link in db because the file longer exists on disk: '{}'".format(abspath))
                item.delete_instance()

        # Mark the last run as now and release the lock
        self.last_run = datetime.datetime.now()
        lock.release()


def get_video_codec_and_resolution_from_streams(file_probe: dict):
    image_video_codecs = [
        'alias_pix',
        'apng',
        'brender_pix',
        'dds',
        'dpx',
        'exr',
        'fits',
        'gif',
        'mjpeg',
        'mjpegb',
        'pam',
        'pbm',
        'pcx',
        'pfm',
        'pgm',
        'pgmyuv',
        'pgx',
        'photocd',
        'pictor',
        'pixlet',
        'png',
        'ppm',
        'ptx',
        'sgi',
        'sunrast',
        'tiff',
        'vc1image',
        'wmv3image',
        'xbm',
        'xface',
        'xpm',
        'xwd',
    ]
    # Require a list of probe streams to continue
    file_probe_streams = file_probe.get('streams', [])
    if not file_probe_streams:
        return False
    # Loop over all streams found in the file probe
    for stream_info in file_probe_streams:
        # Check if this is a video stream
        if stream_info.get('codec_type').lower() == "video":
            # If this is a image stream - ignore it
            if stream_info.get('codec_name').lower() in image_video_codecs:
                continue
            codec_name = stream_info.get('codec_name', '')
            codec_long_name = stream_info.get('codec_long_name')
            # Calculate resolution
            video_width = stream_info.get('width')
            video_height = stream_info.get('height')
            if codec_long_name:
                return codec_long_name, video_width, video_height
            return codec_name, video_width, video_height
    return 'No Video Codec', None, None


def generate_all_video_stats(data):
    arguments = data.get('arguments')
    filter = arguments.get('filter')
    if filter:
        filter = str(filter[0].decode("utf-8"))
    db_data = Data()

    container_names = db_data.get_container_names(filter)
    video_codecs = db_data.get_video_codecs(filter)
    video_resolutions = db_data.get_video_resolutions(filter)
    top_file_paths = db_data.get_top_10_paths(filter)

    return_data = {
        'container_names':   container_names,
        'video_codecs':      video_codecs,
        'video_resolutions': video_resolutions,
        'top_file_paths':    top_file_paths,
    }

    return json.dumps(return_data, indent=2)


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
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    file_probe = probe.get_probe()

    container_name = file_probe.get('format', {}).get('format_long_name')
    video_codec, video_width, video_height = get_video_codec_and_resolution_from_streams(file_probe)

    # Remove files that no longer exist (tested only once a day)
    data_cleanup = DataCleanup()
    data_cleanup.test_outdated_files_still_exist()

    # Add this file's data to the database
    db_data = Data()
    db_data.save_video_file_item(abspath, container_name, video_codec, video_width, video_height)

    return data


def render_frontend_panel(data):
    if data.get('path') in ['videoStats', '/videoStats', '/videoStats/']:
        data['content_type'] = 'application/json'
        data['content'] = generate_all_video_stats(data)
        return

    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'index.html'))) as f:
        content = f.read()
        data['content'] = content.replace("{cache_buster}", str(uuid.uuid4()))

    return data
