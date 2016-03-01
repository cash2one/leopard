define(['app', 'service'], function (app) {

    'use strict';

    app.controller('originalDetailCtrl', ['configFactory', 'financeTools'
        , 'requestProxy', 'messagePrompt', '$scope', '$routeParams', '$modal'
        , '$location', '$rootScope', '$sce', '$interval'
        , function(configFactory, financeTools, requestProxy, messagePrompt, $scope
            , $routeParams, $modal, $location, $rootScope, $sce, $interval){

            var project = {
                    info: {},
                    repaymentPlans: [],
                    user: {},
                    isInvest: $location.path().indexOf('invest')!=-1,
                    isStudent: $location.path().indexOf('student')!=-1
                },
                getProjectConf = configFactory(['getProject'],
                    {params: {project_id: $routeParams['id'],
                    investment_id: $routeParams['id']}});
            $scope.project = project;

            function getData(){

            //get project information
            requestProxy(getProjectConf)
                .success(function(data){
                    project.info = data;
                    project.project_info = data['project'];
                    if (data.remain_bid_time){
                        $scope.remainTime = data.remain_bid_time;
                        launch();
                    }
                    if(project.info.filter_risk_controls){
                        for (var i = 0; i < project.info.filter_risk_controls.length; i++) {
                            project.info.filter_risk_controls[i].content = $sce.trustAsHtml(project.info.filter_risk_controls[i].content);
                        }
                    }
                    project.info.invest_award = project.info.invest_award * 100;

                    project.info.guaranty = $sce.trustAsHtml(project.info.guaranty);

                    //caculation the repayment plans
                    project.repaymentPlans = financeTools.getRepaymentPlan(data.rate, data.amount,
                        data.periods, data.repaymentmethod.logic);
                })
                .error(function(){
                    $location.path('/404');
                });

            //get user's information
            if($scope.CURRENT_USER_ID)
                requestProxy({keyName: 'getUser'})
                    .success(function(data){
                        project.user = data;
                    });
        }
        getData();


    }]);

})
