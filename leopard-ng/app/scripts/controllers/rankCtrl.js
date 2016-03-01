define(['app', 'service', 'config'], function (app) {

    'use strict';

    app.controller('rankCtrl', ['requestProxy', '$scope'
        , function(requestProxy, $scope){
        var rankData = {
            rank: {}
        };

        $scope.rankData = rankData;

        //get rank list
        requestProxy({keyName: 'getRank'})
            .success(function(data){
                rankData.rank = data;
            });
    }]);
})