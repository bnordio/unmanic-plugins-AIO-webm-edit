#!/bin/bash
# -
# File: install-nodejs.sh
# Project: plugins
# File Created: 04 May 2022, 8:03 AM
# Author: josh5
# -----
# Last Modified: 04 May 2022, 8:03 AM
# Modified By: josh5
# -

# Script is executed by the Unmanic container on startup to auto-install dependencies

if ! command -v node &> /dev/null; then
    echo "**** Installing NodeJS ****"
    #[[ "${__apt_updated:-false}" == 'false' ]] && apt-get update && __apt_updated=true
    curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
    apt-get install -y nodejs
else
    echo "**** NodeJS already installed ****"
fi
