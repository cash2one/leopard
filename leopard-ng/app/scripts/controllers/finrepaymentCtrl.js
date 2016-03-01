define(['app', 'service'], function (app) {

    'use strict';

    app.controller('finrepaymentCtrl', ['filterConfigProduce'
        , 'configFactory', 'requestProxy', 'financeTools', '$scope', '$modal'
        , function(filterConfigProduce, configFactory, requestProxy
            , financeTools, $scope, $modal){
        var filterConfig = {
                types: [{
                    title: '项目状态',
                    name: 'status',
                    values: filterConfigProduce('repay')
                }],
                getData: getData
            },
            requestConf = configFactory(['getFinRepayments']),
            paginationConf = {
                item: null,
                current: 0,
                total: null,
                getData: getData
            },
            listData = {
                list: []
            },
            repaymentModal = null;

        $scope.filterConfig = filterConfig;
        $scope.paginationConf = paginationConf;
        $scope.listData = listData;
        requestConf.params = {};

        function getData(conf){
            if(typeof(conf) == 'object'){
                paginationConf.item = null;
                requestConf.params['filter'] = conf;
            }
            else if(conf){
                requestConf.params['offset'] = (conf - 1)*paginationConf.item;
            }
            requestProxy(requestConf)
                .success(function(data, status, headers){
                    if(!paginationConf.item){
                        paginationConf.item = data.length;
                        paginationConf.total = data.length * headers('Page-total');
                    }

                    for(var i = 0; i<data.length; i++) {
                        data[i].interest = financeTools.getInterest(
                            data[i].rate, data[i].amount, data[i].periods,
                            data[i].repaymentmethod.logic);
                        if(data[i].repaymentmethod.logic === 'repayment_immediately' ||
                          data[i].repaymentmethod.logic === 'one_only')
                            data[i].total_period = 1;
                        else
                            data[i].total_period = data[i].periods
                    }
                    listData.list = data;
                });
        }
        getData();

        //set a modal
        $scope.showPlan = function (project){
            if(repaymentModal){
                repaymentModal.close();
            }
            repaymentModal = $modal.open({
                templateUrl: 'plans_modal.html',
                controller: ['$scope', '$modalInstance', 'project', 'getData'
                , 'messagePrompt'
                , plansModalIns],
                resolve: {
                    project: function(){
                        return project;
                    },
                    getData: function(){
                        return getData;
                    }
                }
            });
        }
        //set a modal controller
        var plansModalIns = function($scope, $modalInstance, project, getData, messagePrompt){
            var planData = {
                    project: project,
                    list: project.plans,
                    tradePass: null
                };
            $scope.planData = planData;

            function getFinRepaymentData(project) {
                var conf = configFactory(['getFinRepaymentPlans'], {params: {project_id: project.id, sort: 'id asc'}});
                requestProxy(conf)
                    .success(function(data, status, headers){
                        for(var i=0; i<data.length; i++){
                            data[i].operationEnable = data[i].status == 100
                             && (data[i].period -1) <= project.paid_periods;
                        }
                        planData.list = data;
                    });
            }
            getFinRepaymentData(project);

            $scope.repay = function(project, repayment){
                if(!planData.tradePass){
                    messagePrompt.forbidden('请先输入交易密码 !');
                    return;
                }
                var repayConf = configFactory(['repayFinRepaymentPlan']
                    , {params: {project_id: project.id
                                ,repayment_id: repayment.id}
                       , data:{trade_password: planData.tradePass}});

                requestProxy(repayConf)
                    .success(function(data){
                        project.paid_periods += 1;
                        planData.tradePass = '';
                        getFinRepaymentData(project);
                        messagePrompt.success(data.message);
                    });
            }

            $scope.cancel = function(){
                $modalInstance.dismiss();
                getData();
            };
        };
    }]);
})