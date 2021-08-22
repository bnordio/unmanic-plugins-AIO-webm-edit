#!/bin/bash

repo_root_path=$(readlink -e $(dirname "${BASH_SOURCE[0]}")/)

plugin_ids=(
    "encoder_video_h264_libx264"
    "encoder_video_h264_nvenc"
    "encoder_video_hevc_libx265"
    "encoder_video_hevc_nvenc"
    "mover2"
    "path_ignore"
    "postprocessor_script"
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
