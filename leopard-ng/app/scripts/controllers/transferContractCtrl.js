define(['app', 'service', 'config'], function (app) {

    'use strict';

    app.controller('transferContractCtrl', ['messagePrompt', 'configFactory', 'requestProxy', 'financeTools', '$scope'
        , '$routeParams', '$location'
        , function(messagePrompt, configFactory, requestProxy, financeTools, $scope, $routeParams, $location){
        var contractData = {
                info: null
            },
            contractId = $routeParams['id'],
            requestConf = {};
        $scope.contractData = contractData;

        //produce post config
        requestConf = configFactory(['getTransferContract'], {params: {investment_id: contractId}});
        //get infomation of guarantee
        requestProxy(requestConf)
            .success(function(data){
                contractData.info = data;
            })
            .error(function(data){
                messagePrompt.error(data.message);

                setTimeout(function(){
                    $location.path('/404');
                }, 1600);

            });
    }]);
})
