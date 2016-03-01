define(['app', 'service'], function (app) {

    'use strict';

    app.controller('homeCtrl', ['configFactory', 'requestProxy', '$scope', function(configFactory, requestProxy, $scope){
        var homeData = {
            projectList: [],
            studentProjectList: [],
            assignmentList: [],
            noticeList: [],
            reportList: [],
            advanceProject: null,
            platformInfo: {
                gross_income: 0,
                users_income: 0,
                turnover: 0
            },
            now: new Date()
        }
        $scope.homeData = homeData;

        //read request config
        var projectConf = configFactory(['getProjectList']
            , {params: {limit: 3, sort: 'status asc|id desc'}});
        //get project list
        requestProxy(projectConf)
            .success(function(data){
                homeData.projectList = data;
            });

        //read request config
        var studentProjectConf = configFactory(['getStudentProjectList']
            , {params: {limit: 1, sort: 'status asc|id desc'}});
        //get student project list
        requestProxy(studentProjectConf)
            .success(function(data){
                homeData.studentProjectList = data;
            });

        //read request config
        var assignmnetConf = configFactory(['getAssignmentList']
            , {params: {limit: 3, sort: 'status asc|id desc'}});
        //get project list
        requestProxy(assignmnetConf)
            .success(function(data){
                homeData.assignmentList = data;
            });

        // get platform info
        var platformInfoConf = configFactory(['getPlatformInfo']);
        requestProxy(platformInfoConf)
            .success(function(data){
                homeData.platformInfo = data;
            });

        //read post request config
        var noticeConf = configFactory(['getPosts']
            , {params: {limit: 10, filter: {type: 50}}}),
            reportConf = configFactory(['getPosts']
            , {params: {limit: 5, filter: {type: 51}}}),
            advanceConf = configFactory(['getPosts']
            , {params: {limit: 1, filter: {type: 53}}});
        //get post list
        requestProxy(noticeConf)
            .success(function(data){
                homeData.noticeList = data;
            });
        requestProxy(reportConf)
            .success(function(data){
                homeData.reportList = data;
            });
        requestProxy(advanceConf)
            .success(function(data){
                homeData.advanceProject = data[0];
            });
    }]);
})
