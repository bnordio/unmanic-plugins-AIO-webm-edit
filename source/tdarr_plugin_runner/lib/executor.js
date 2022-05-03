const yargs = require('yargs');
const fs = require('fs');
const path = require('path');
const importFresh = require('import-fresh');
const home = require("os").homedir();


const getHomePath = function () {
    let homePath;
    if (process.env.NODE_ENV == "production") {
        if (process.env.DATA) {
            homePath = process.env.DATA;
        } else {
            homePath = home + "/Documents";
        }
    } else {
        //set dev env
        homePath = home + "/Documents";
    }
    return homePath;
}

const PluginMetadata = function (pluginId) {
    let pluginLocalPath = path.join(path.dirname(__filename), '..', 'Tdarr_Plugins-master', 'Community', pluginId + '.js');
    let plugin = importFresh(pluginLocalPath);
    let pluginDetails = plugin.details();
    return {
        pluginDetails: pluginDetails,
        pluginLocalPath: pluginLocalPath,
    };
}

const ParsePluginDetails = function (argv) {
    let functionResponse = {
        success: false,
        errors: [],
        data: {},
    }

    try {
        let pluginMetadata = PluginMetadata(argv.id);
        functionResponse.success = true;
        functionResponse.data = pluginMetadata.pluginDetails;
    } catch (err) {
        functionResponse.errors.push(err);
    }
    return functionResponse;
}

const ParseParamsFile = function (paramsFile) {
    let rawdata = fs.readFileSync(paramsFile);
    return JSON.parse(rawdata);
}

const DumpResultsFile = function (outputFile, results_dictionary) {
    //let resultsFile = paramsFile.replace(/\.[^.$]+$/, '') + '-results.json';
    console.log(results_dictionary);
    let json_data = JSON.stringify(results_dictionary);
    fs.writeFileSync(outputFile, json_data);
}

const ExecPlugin = function (argv) {
    let functionResponse = {
        success: false,
        errors: [],
        data: {},
    }

    try {
        let params = ParseParamsFile(argv.parameters)

        const firstItem = params.file;
        const homePath = getHomePath();

        let pluginMetadata = PluginMetadata(argv.id);

        let pluginLocalPath = pluginMetadata.pluginLocalPath;

        let otherArguments = {
            homePath: homePath,
            handbrakePath: params.otherArguments.handbrakePath,
            ffmpegPath: params.otherArguments.ffmpegPath,
            originalLibraryFile: params.otherArguments.originalLibraryFile,
        };
        let librarySettings = params.librarySettings;
        let plugin = importFresh(pluginLocalPath);

        // Set plugin inputs
        var pluginInputs = params.inputs;


        var response = plugin.plugin(
            firstItem,
            librarySettings,
            pluginInputs,
            otherArguments,
        );

        functionResponse.success = true;
        functionResponse.data = response;
    } catch (err) {
        functionResponse.errors.push(err);
    }
    return functionResponse;
}

const argv = yargs
    .option('id', {
        describe: 'The ID of the plugin to call',
    })
    .demandOption(['id'])
    .command('details', 'Print details and config of a given plugin', (yargs) => {
        return yargs
    }, (argv) => {
        console.log(JSON.stringify(ParsePluginDetails(argv)));
    })
    .command('plugin', 'Execute a given plugin', (yargs) => {
        return yargs
            .option('parameters', {
                describe: 'The path to the parameters file',
                default: null,
            })
            .demandOption(['parameters'])
            .option('output', {
                describe: 'The path to the results file',
                default: null,
            })
            .demandOption(['output'])
    }, (argv) => {
        let results = ExecPlugin(argv);
        DumpResultsFile(argv.output, results);
    })
    .help().alias('help', 'h').argv;
