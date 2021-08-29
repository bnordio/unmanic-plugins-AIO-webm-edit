#!/bin/bash
#
# Generate a plugin PR for the official repo
#

official_git_repo="git@github.com:Unmanic/unmanic-plugins.git"
repo_root_path=$(readlink -e $(dirname "${BASH_SOURCE[0]}")/)

plugin_id="${@}"

if [[ -z ${plugin_id} ]]; then
    echo "You forgot to provide the ID of one of your plugins..."
    exit 1
fi


echo "Generating PR for plugin ${plugin_id}"
tmp_dir=$(mktemp -d --suffix='-unmanic-plugin-pr')


# Clone plugin to temp directory
echo -e "\n*** Cloning plugin git repo to '${tmp_dir}/${plugin_id}'"
git clone --depth=1 --branch master --single-branch "git@github.com:Josh5/unmanic.plugin.${plugin_id}" "${tmp_dir}/${plugin_id}"
[[ $? -gt 0 ]] && echo "Failed to fetch the plugin git repository. Exit!" && exit 1;


# Clone the origin unmanic-plugins repository
origin_url=$(git config --get remote.origin.url)
git clone --depth=1 --branch official --single-branch "${origin_url}" "${tmp_dir}/unmanic-plugins"
[[ $? -gt 0 ]] && echo "Failed to fetch the unmanic-plugins git repository. Exit!" && exit 1;


########################################################################
### PULL OFFICIAL UPSTREAM
pushd "${tmp_dir}/unmanic-plugins" &> /dev/null
# Add upstream remote
echo -e "\n*** Adding upstream git repo"
git remote add upstream "${official_git_repo}"
# Pull changes from upstream
git pull upstream official
[[ $? -gt 0 ]] && echo "Failed to pull in changes from the official git repository. Exit!" && exit 1;
popd &> /dev/null


########################################################################
### CREATE PR BRANCH
pushd "${tmp_dir}/unmanic-plugins" &> /dev/null
# Create PR branch 
echo -e "\n*** Checkout PR branch for plugin"
git checkout -b "pr-${plugin_id}"
popd &> /dev/null


########################################################################
### UPDATE SUBMODULES
pushd "${tmp_dir}/${plugin_id}" &> /dev/null
# Update any submodules
echo -e "\n*** Pulling plugin submodules"
git submodule update --init --recursive 
popd &> /dev/null


########################################################################
### BUILD/INSTALL
pushd "${tmp_dir}/unmanic-plugins" &> /dev/null
# Install/update plugin files
echo -e "\n*** Installing files from plugin git repo to this repository's source directory"
rsync -avh --delete \
    --exclude='.git/' \
    --exclude='.gitmodules' \
    --exclude='.idea/' \
    "${tmp_dir}/${plugin_id}/" "${tmp_dir}/unmanic-plugins/source/${plugin_id}"
# Read plugin version
plugin_version=$(cat ${tmp_dir}/${plugin_id}/info.json | jq -rc '.version')
[[ ${plugin_version} == "null" ]] && echo "Failed to fetch the plugin's version from the info.json file. Exit!" && exit 1;
popd &> /dev/null


########################################################################
### COMMIT
pushd "${tmp_dir}/unmanic-plugins" &> /dev/null
echo -e "\n*** Commit changes in unmanic-plugins repository"
commit_message="[${plugin_id}] v${plugin_version}"
echo ${commit_message}
git add .
git commit -m "${commit_message}"
if [[ $? -gt 0 ]]; then
    echo
    echo "No commit created. Possibly because there was nothing to commit!"
    echo "PR branch will not be pushed." 
    exit 1
fi
popd &> /dev/null


########################################################################
### PUBLISH
pushd "${tmp_dir}/unmanic-plugins" &> /dev/null
echo -e "\n*** Publish changes to origin unmanic-plugins repository"
git push -f origin "pr-${plugin_id}"
popd &> /dev/null
