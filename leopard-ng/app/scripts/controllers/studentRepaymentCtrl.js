define(['app', 'service'], function (app) {

    'use strict';

    app.controller('studentRepaymentCtrl', ['$scope', '$modal'
        , function($scope, $modal){
        var repaymentModal = null;

        //set a modal
        $scope.showPlan = function (project){
            if(repaymentModal){
                repaymentModal.close();
            }
            repaymentModal = $modal.open({
                templateUrl: 'student_plans_modal.html',
                controller: ['$scope', '$modalInstance', 'project', 'requestProxy'
                    , 'configFactory', 'messagePrompt'
                , plansModalIns],
                resolve: {
                    project: function(){
                        return project;
                    }
                }
            });
        }
        //set a modal controller
        var plansModalIns = function($scope, $modalInstance, project, requestProxy
            , configFactory, messagePrompt){
            var planData = {
                project: project,
                list: null
            }

            $scope.planData = planData;

            requestProxy(configFactory(['getStudentRepayments'], {params: {id: project.id}}))
                .success(function(data){
                    planData.list = data;
                });

            $scope.repayProject = function(id, $index){
                requestProxy(configFactory(['repayStudentRepayment'],
                    {params: {project_id: project.id, plan_id: id}}))
                    .success(function(data){
                        messagePrompt.success(data.message);
                        planData.list[$index].executed_time = new Date();
                        planData.list[$index].status = 200;
                    });
            }

            $scope.cancel = function(){
                $modalInstance.dismiss();
            };
        };
    }]);
})
