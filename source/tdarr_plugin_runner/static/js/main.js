// Global variables
let selectedLibraryID;
let selectedLibraryName;
let uninstalledPlugins;
let installedPluginData;
let installedPluginsList;
let enabledPluginsList;
let installedPluginSettings;

const Main = function () {

    const updateLibraryOptions = function () {

        const reloadPageWithNewLibrary = function (libraryId) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('library_id', libraryId);
            window.location.search = urlParams;
        }

        const setNavLibraryParam = function () {
            const navLibrary = document.getElementById("nav_library");
            navLibrary.href = './page_libraries?library_id=' + selectedLibraryID;

            const navOptions = document.getElementById("nav_options");
            navOptions.href = './page_options?library_id=' + selectedLibraryID;
        }

        const selectLibrary = function (libraryId, libraryName) {
            console.log("Selecting library " + libraryId + " - " + libraryName)
            selectedLibraryID = libraryId;
            selectedLibraryName = libraryName

            const libraryNameHeader = document.getElementById("selected_library_header");
            const libraryIdInput = document.getElementById("library_id");

            libraryNameHeader.textContent = selectedLibraryName;
            libraryIdInput.value = selectedLibraryID;
            libraryIdInput.dispatchEvent(new Event('change'));

            // Set nav tab options
            setNavLibraryParam()

            // Set the current url params
            //setLibraryInUrlParams()
        }

        jQuery.get('/unmanic/api/v2/settings/libraries', function (response) {
            // Get currently selected library from params
            let currentLibrary = 1;
            const urlParams = new URLSearchParams(window.location.search);
            const setLibraryId = urlParams.get('library_id');
            console.log(setLibraryId)
            if (setLibraryId) {
                currentLibrary = parseInt(setLibraryId);
            }

            // Select the dropdown list container
            let librarySelections = document.getElementById("library_selections_container");

            // Empty it out
            librarySelections.innerHTML = "";

            // Fill the list with the libraries
            for (let i = 0; i < response.libraries.length; i++) {
                let library = response.libraries[i];
                // Create node
                let node = document.createElement("a");
                node.appendChild(document.createTextNode(library.name));
                node.className = "dropdown-item";
                node.href = "#";
                node.onclick = function () {
                    // TODO: Speed up switching libraries without a page reload
                    reloadPageWithNewLibrary(library.id);
                    //selectLibrary(library.id, library.name);
                }
                librarySelections.appendChild(node);

                // Set the selected library
                if (parseInt(library.id) === currentLibrary) {
                    // Default to the default library (1)
                    selectLibrary(currentLibrary, library.name);
                }
            }
        });
    }

    return {
        init: function () {
            // Update library selections. Make sure the default library is selected for this init call of the function
            updateLibraryOptions();
            //updateInstallerList();
        }
    };

}();
