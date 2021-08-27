#!/bin/bash
# -
# File: pull_in_my_plugins.sh
# Project: unmanic-plugins
# File Created: Sunday, 22nd August 2021 11:38:59 pm
# Author: Josh.5 (jsunnex@gmail.com)
# -----
# Last Modified: Friday, 27th August 2021 5:01:07 pm
# Modified By: Josh.5 (jsunnex@gmail.com)
# -

repo_root_path=$(readlink -e $(dirname "${BASH_SOURCE[0]}")/)

plugin_ids=(
    "dts_to_dd"
    "encoder_audio_aac"
    "encoder_audio_ac3"
    "encoder_video_h264_libx264"
    "encoder_video_h264_nvenc"
    "encoder_video_hevc_libx265"
    "encoder_video_hevc_nvenc"
    "encoder_video_hevc_vaapi"
    "encoder_video_libvpx_vp9"
    "extract_srt_subtitles_to_files"
    "file_size_metrics"
    "ignore_under_size"
    "limit_library_search_by_file_extension"
    "mover2"
    "normalise_aac"
    "notify_plex"
    "path_ignore"
    "postprocessor_script"
    "remove_all_subtitles"
    "reorder_audio_streams_by_language"
    "reorder_subtitle_streams_by_language"
    "strip_image_streams"
    "video_trim"
)

pushd "${repo_root_path}" &> /dev/null


for plugin_id in "${plugin_ids[@]}"; do

    echo "Processing plugin ${plugin_id}"
    tmp_dir=$(mktemp -d --suffix='-unmanic-plugin')

    # Clone plugin to temp directory
    echo -e "\n*** Cloning plugin git repo to '${tmp_dir}/${plugin_id}'"
    git clone --depth=1 --branch master --single-branch "git@github.com:Josh5/unmanic.plugin.${plugin_id}" "${tmp_dir}/${plugin_id}"
    pushd "${tmp_dir}/${plugin_id}" &> /dev/null

    # Pull files from plugin to this source directory
    echo -e "\n*** Pulling plugin submodules"
    git submodule update --init --recursive 

    # Install/update plugin files
    echo -e "\n*** Installing files from plugin git repo to this repository's source directory"
    rsync -avh --delete \
        --exclude='.git/' \
        --exclude='.gitmodules' \
        --exclude='.idea/' \
        "${tmp_dir}/${plugin_id}/" "${repo_root_path}/source/${plugin_id}"

    popd &> /dev/null

done

popd &> /dev/null
