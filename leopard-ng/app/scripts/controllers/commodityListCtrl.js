define(['app', 'service'], function (app) {

    'use strict';

    app.controller('commodityListCtrl', ['configFactory', 'requestProxy', '$scope', function(configFactory, requestProxy, $scope){
        var homeData = {
            productList: [],
        }
        $scope.homeData = homeData;

        //read request config
        var productConf = configFactory(['getMallProduct']
            , {params: {limit: 50, sort: 'priority desc|id desc'}});
        //get project list
        requestProxy(productConf)
            .success(function(data){
                homeData.productList = data;
            });
    }]);
})
