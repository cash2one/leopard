define(['app', 'service'], function (app) {

    'use strict';

    app.controller('borrowingCtrl', ['filterConfigProduce'
        , 'configFactory', 'requestProxy', 'financeTools', '$scope', '$modal'
        , function(filterConfigProduce, configFactory, requestProxy
            , financeTools, $scope, $modal){
        var filterConfig = {
                types: [{
                    title: '项目状态',
                    name: 'status',
                    values: filterConfigProduce('lend')
                }],
                getData: getData
            },
            requestConf = configFactory(['getBorrowing']),
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
                controller: ['$scope', '$modalInstance', 'requestProxy'
                , 'configFactory', 'messagePrompt', 'project', 'getData', plansModalIns],
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
        var plansModalIns = function($scope, $modalInstance, requestProxy
                , configFactory, messagePrompt, project, getData){
            var planData = {
                    project: project,
                    tradePass: null
                };
            $scope.planData = planData;

            $scope.ok = function(){
                if(!planData.tradePass){
                    messagePrompt.forbidden('请先输入交易密码 !');
                    return;
                }
                var repayAllConf = configFactory(['repayProject']
                    , {params: {project_id: project.id
                        , trade_password: planData.tradePass}});
                requestProxy(repayAllConf)
                    .success(function(data){
                        messagePrompt.success(data.message);
                        $modalInstance.close();
                        getData();
                    });
            }
            $scope.cancel = function(){
                $modalInstance.dismiss();
            };
        };
    }]);
})