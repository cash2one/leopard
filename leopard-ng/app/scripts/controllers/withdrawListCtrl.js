define(['app', 'service'], function (app) {

    'use strict';

    app.controller('withdrawListCtrl', ['filterConfigProduce'
        , 'configFactory', 'requestProxy', 'financeTools', '$scope', '$modal'
        , function(filterConfigProduce, configFactory, requestProxy
            , financeTools, $scope, $modal){
        var filterConfig = {
                types: [{
                    title: '提现状态',
                    name: 'status',
                    values: filterConfigProduce('withdraw')
                }],
                getData: getData
            },
            requestConf = configFactory(['getWithdraw']),
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
        $scope.cancelWithdraw = function (id){
            if(repaymentModal){
                repaymentModal.close();
            }
            repaymentModal = $modal.open({
                templateUrl: 'confirm_modal.html',
                controller: ['$scope', '$modalInstance', 'id'
                , 'getData', 'requestProxy', 'configFactory'
                , 'messagePrompt', plansModalIns],
                resolve: {
                    id: function(){
                        return id;
                    },
                    getData: function(){
                        return getData;
                    }
                }
            });
        }
        //set a modal controller
        var plansModalIns = function($scope, $modalInstance, id
            , getData, requestProxy, configFactory, messagePrompt){

            var conf = configFactory(['cancelWithdraw'], {params: {withdraw_id: id}});
            
            $scope.ok = function(){
                requestProxy(conf)
                    .success(function(){
                        messagePrompt.success('提现取消成功!');
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