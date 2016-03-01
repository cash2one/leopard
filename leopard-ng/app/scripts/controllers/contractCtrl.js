define(['app', 'service', 'config'], function (app) {

    'use strict';

    app.controller('contractCtrl', ['configFactory', 'requestProxy', 'financeTools', '$scope'
        , '$routeParams', '$location'
        , function(configFactory, requestProxy, financeTools, $scope, $routeParams, $location){
        var contractData = {
                info: null,
                upperAmount: ''
            },
            contractId = $routeParams['id'],
            requestConf = {};
        $scope.contractData = contractData;

        //produce post config
        requestConf = configFactory(['getContract'], {params: {investment_id: contractId}});
        //get infomation of guarantee
        requestProxy(requestConf)
            .success(function(data){
                contractData.info = data;
                contractData.upperAmount = financeTools.getUpperAmount(data.project.amount);
            })
            .error(function(){
                $location.path('/404');
            });
    }]);
})