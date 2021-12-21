// Set new default font family and font color to mimic Bootstrap's default styling
Chart.defaults.global.defaultFontFamily = 'Nunito', '-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';
Chart.defaults.global.defaultFontColor = '#858796';


// Randomly select a colour
const randomColour = () => {
    // Generate x2 random hex characters
    let n1 = Math.floor(Math.random() * 16).toString(16);
    let n2 = Math.floor(Math.random() * 16).toString(16);
    // Predefine a pattern so we are generating colours within that pattern
    const number = '0' + n1 + n2 + 'FDD';
    // Return the HEX colour
    return "#" + number;
}

// Use randomly generated colours as our chart background colours
let chartBackgroundColours = []
for (let count = 0; count < 100; count++) {
    chartBackgroundColours.push(randomColour())
}


var VideoStats = function () {
    // Video Containers
    let videoContainersPieChart = new Chart(document.getElementById("videoContainers"), {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [
                {
                    data: [],
                    backgroundColor: chartBackgroundColours,
                    hoverBorderColor: "rgba(234, 236, 244, 1)",
                }
            ],
        },
        options: {
            maintainAspectRatio: false,
            tooltips: {
                backgroundColor: "rgb(255,255,255)",
                bodyFontColor: "#858796",
                borderColor: '#dddfeb',
                borderWidth: 1,
                xPadding: 15,
                yPadding: 15,
                displayColors: false,
                caretPadding: 10,
            },
            legend: {
                display: false
            },
            cutoutPercentage: 80,
        },
    });

    // Video Codecs
    let videoCodecsPieChart = new Chart(document.getElementById("videoCodecs"), {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [
                {
                    data: [],
                    backgroundColor: chartBackgroundColours,
                    hoverBorderColor: "rgba(234, 236, 244, 1)",
                }
            ],
        },
        options: {
            maintainAspectRatio: false,
            tooltips: {
                backgroundColor: "rgb(255,255,255)",
                bodyFontColor: "#858796",
                borderColor: '#dddfeb',
                borderWidth: 1,
                xPadding: 15,
                yPadding: 15,
                displayColors: false,
                caretPadding: 10,
            },
            legend: {
                display: false
            },
            cutoutPercentage: 80,
        },
    });

    // Video Resolutions
    let videoResolutionsPieChart = new Chart(document.getElementById("videoResolutions"), {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [
                {
                    data: [],
                    backgroundColor: chartBackgroundColours,
                    hoverBorderColor: "rgba(234, 236, 244, 1)",
                }
            ],
        },
        options: {
            maintainAspectRatio: false,
            tooltips: {
                backgroundColor: "rgb(255,255,255)",
                bodyFontColor: "#858796",
                borderColor: '#dddfeb',
                borderWidth: 1,
                xPadding: 15,
                yPadding: 15,
                displayColors: false,
                caretPadding: 10,
            },
            legend: {
                display: false
            },
            cutoutPercentage: 80,
        },
    });

    function removeChartData(chart) {
        chart.data.labels.pop();
        chart.data.datasets.forEach((dataset) => {
            dataset.data.pop();
        });
    }

    function removeAllChartData(chart) {
        chart.data.labels = [];
        chart.data.datasets.forEach((dataset) => {
            dataset.data = [];
        });
    }

    function addChartData(chart, label, data) {
        chart.data.labels.push(label);
        chart.data.datasets.forEach((dataset) => {
            dataset.data.push(data);
        });
    }

    const processContainerNames = function (containerNames) {
        removeAllChartData(videoContainersPieChart);
        for (let i = 0; i < containerNames.length; i++) {
            let item = containerNames[i];
            addChartData(videoContainersPieChart, item.container_name, item.count)
        }
        videoContainersPieChart.update();
    };
    const processVideoCodecs = function (videoCodecs) {
        removeAllChartData(videoCodecsPieChart);
        for (let i = 0; i < videoCodecs.length; i++) {
            let item = videoCodecs[i];
            addChartData(videoCodecsPieChart, item.video_codec, item.count)
        }
        videoCodecsPieChart.update();
    };
    const processResoloutions = function (videoResolutions) {
        removeAllChartData(videoResolutionsPieChart);
        for (let i = 0; i < videoResolutions.length; i++) {
            let item = videoResolutions[i];
            addChartData(videoResolutionsPieChart, item.resolution, item.count)
        }
        videoResolutionsPieChart.update();
    };

    const processTopPathsList = function (filePaths) {
        let ul = document.getElementById("pathsList");
        // Clear out list
        ul.innerHTML = '';
        // Add new elements for each result (limit to 10 results)
        for (let i = 0; i < filePaths.length; i++) {
            let item = filePaths[i];
            let li = document.createElement("li");
            li.className = "list-group-item";
            li.appendChild(document.createTextNode(item.abspath));
            ul.appendChild(li);
        }
    }

    const fetchVideoStats = function () {
        let filter = encodeURI(document.getElementById("pathFilter").value);
        jQuery.get('videoStats?filter=' + filter, function (data) {
            processContainerNames(data.container_names)
            processVideoCodecs(data.video_codecs)
            processResoloutions(data.video_resolutions)
            processTopPathsList(data.top_file_paths)
        });
    };

    return {
        //main function to initiate the module
        update: function () {
            fetchVideoStats();
        }
    };

}();
