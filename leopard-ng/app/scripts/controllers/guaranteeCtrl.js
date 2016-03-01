define(['app', 'service', 'config'], function (app) {

    'use strict';

    app.controller('guaranteeCtrl', ['configFactory', 'requestProxy', '$scope'
        , '$routeParams', '$location', '$sce'
        , function(configFactory, requestProxy, $scope, $routeParams, $location
            , $sce){
        var guaranteeData = {
                info: null
            },
            guaranteeId = $routeParams['id'],
            requestConf = {};
        $scope.guaranteeData = guaranteeData;

        //produce post config
        requestConf = configFactory(['getGuarantee'], {params: {id: guaranteeId}});

        //get infomation of guarantee
        requestProxy(requestConf)
            .success(function(data){
                guaranteeData.info = data;
                guaranteeData.info.description = $sce.trustAsHtml(data.description);
            })
            .error(function(){
                $location.path('/404');
            });
    }]);
})