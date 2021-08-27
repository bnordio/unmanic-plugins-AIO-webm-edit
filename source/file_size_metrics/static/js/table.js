var viewConversionDetails = function (jobId) {
    $('#selected_task_id').val(jobId).triggerHandler('change');;
    // Get conversion details template for this item
    //$.get('conversionDetails/?task_id=' + jobId, function (data) {
    //    // update/set the conversion details list
    //    // $('#task_details_content').html(data);
    //    // $('#task_details').removeClass('hidden');
    //    console.log(data)
    //    // // Highlight the currently selected task
    //    // $('.completed_task').css('background', ''); // Remove highlight on all rows
    //    // $('.completed_task_jobid_' + jobId).css('background', 'rgba(197, 185, 107, 0.20)');
    //});
};

var CompletedTasksDatatable = function () {

    var recordName = function (task_label) {
        return '<span class="wrap"> ' + task_label + ' </span>';
    };
    var recordSuccessStatus = function (task_success) {
        var html = '';
        if (task_success) {
            html = '<span class="label label-sm label-success"> Success </span>';
        } else {
            html = '<span class="label label-sm label-danger"> Failed </span>';
        }
        return html;
    };
    var recordActionButton = function (data) {
        var row_id = data.id;
        return '<a class="view-btn" ' +
            'onclick="viewConversionDetails(' + $.trim(row_id) + ');"> View details &#x25B2;\n' +
            '</a>';
    };

    var buildTable = function () {
        console.log("HERE2")
        $('#history_completed_tasks_table').DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: "list/", // ajax source
                type: "GET", // request type
                data: function (data) {
                    return {
                        data: JSON.stringify(data)
                    }
                }
            },
            columnDefs: [
                {
                    targets: 0,
                    title: "Task Name",
                    className: "task_label",
                    name: "task_label",
                    data: "task_label",
                },
                {
                    targets: 1,
                    className: "start_time",
                    title: "Start Time",
                    name: "start_time",
                    data: "start_time",
                },
                {
                    targets: 2,
                    title: "Finish Time",
                    name: "finish_time",
                    data: "finish_time",
                },
                {
                    targets: 3,
                    title: "Status",
                    name: "task_success",
                    data: "task_success",
                    render: recordSuccessStatus,
                },
                {
                    targets: 4,
                    title: "View Details",
                    data: null,
                    searchable: false,
                    orderable: false,
                    mRender: recordActionButton,
                },
            ],

            lengthMenu: [
                [5, 10, 20, 50, 100, 500],
                [5, 10, 20, 50, 100, 500] // change per page values here
            ],
            pageLength: 5, // default record count per page
            order: [
                [2, "desc"]
            ]

        });
    };

    return {
        //main function to initiate the module
        init: function () {
            buildTable();
        }

    };

}();
