define(['app', 'service'], function (app) {

    'use strict';

    app.controller('assignmentCtrl', ['$scope', 'filterConfigProduce'
        , 'configFactory', 'requestProxy', '$modal'
        , function($scope, filterConfigProduce, configFactory, requestProxy, $modal){
        var filterConfig = {
                types: [{
                    title: '项目状态',
                    name: 'status',
                    values: filterConfigProduce('invest')
                }],
                getData: getData
            },
            requestConf = configFactory(['getAssignmentList']),
            paginationConf = {
                item: null,
                current: 0,
                total: null,
                getData: getData
            },
            listData = {
                list: []
            },
            investModal = null;

        $scope.filterConfig = filterConfig;
        $scope.paginationConf = paginationConf;
        $scope.listData = listData;
        requestConf.params = {limit: 10, sort: 'status asc|id desc'};

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
        $scope.showPlans = function (invest){
            if(investModal){
                investModal.close();
            }
            investModal = $modal.open({
                templateUrl: 'plans_modal.html',
                controller: ['$scope', '$modalInstance', 'invest', plansModalIns],
                resolve: {
                    invest: function(){
                        return invest;
                    }
                }
            });
        }
        //set a modal controller
        var plansModalIns = function($scope, $modalInstance, invest){
            $scope.invest = invest;
            $scope.cancel = function () {
                $modalInstance.dismiss();
            };
        };

        //set a modal
        $scope.assignment = function (invest, type){
            if(investModal){
                investModal.close();
            }
            investModal = $modal.open({
                templateUrl: 'assignment_modal.html',
                controller: ['$scope', '$modalInstance', 'invest', 'type', 'requestProxy'
            , 'configFactory', 'messagePrompt', assignmentModalIns],
                resolve: {
                    invest: function(){
                        return invest;
                    },
                    type: function(){
                        return type;
                    }
                }
            });
        }
        //set a modal controller
        var assignmentModalIns = function($scope, $modalInstance, invest, type
            , requestProxy, configFactory, messagePrompt){
            var assignmentInfo = {
                    tradePass: null,
                    payAmount: 0,
                    type: type,
                    investment: invest
                },
                conf = type?conf = configFactory(['createAssignment']
                        , {params: {investment_id: invest.id, pay_amount: 0}
                        , data: {trade_password: null}})
                    : configFactory(['removeAssignment']
                        , {params: {investment_id: invest.id, trade_password: null}}
                        );
            $scope.assignmentInfo = assignmentInfo;
            $scope.ok = function(){
                if(!assignmentInfo.tradePass){
                    messagePrompt.forbidden('请先输入交易密码 !');
                    return;
                }
                conf.params.pay_amount = assignmentInfo.payAmount;
                var re = /^[-]?[0-9]+[\.]?[0-9]*$/;
                if(!re.test(conf.params.pay_amount)){
                    messagePrompt.forbidden('贴现金额格式错误!');
                    return;
                }
                if(type)
                    conf.data.trade_password = assignmentInfo.tradePass;
                else
                    conf.params.trade_password = assignmentInfo.tradePass;

                requestProxy(conf)
                    .success(function(){
                        if(type){
                            messagePrompt.success('申请成功 !该项目已发布到转让市场');
                            invest.status = 300;
                        }else{
                            messagePrompt.success('取消转让成功 !');
                            invest.status = 200;
                        }
                    });
                assignmentInfo.tradePass = null;
                $modalInstance.close();
            }
            $scope.cancel = function () {
                assignmentInfo.tradePass = null;
                $modalInstance.dismiss();
            };
        };
    }]);
})
