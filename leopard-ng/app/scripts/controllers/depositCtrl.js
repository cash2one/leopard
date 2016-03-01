define(['app', 'service'], function (app) {

    'use strict';

    app.controller('depositCtrl', ['financeTools', 'requestProxy', 'messagePrompt'
        , '$scope', '$location', '$timeout', '$cookies'
        , function(financeTools, requestProxy, messagePrompt, $scope, $location, $timeout, $cookies){

        var depositControls = {
                conf: {
                    keyName: 'createDeposit'
                },
                amount: {
                    label: '金额',
                    name: 'amount',
                    pattern: '/^\\d+(\\.\\d{1,2})?$/',
                    min: 1,
                    require: true
                },
                serial: {
                    label: '流水号',
                    name: 'comment',
                    require: true
                },
                platform: {
                    label: '充值平台',
                    name: 'platform'
                },
                models: {
                    amount: null,
                    serial: null,
                    platform: null
                }
            },
            depositData = {
                platformList: [],
                platform: null,
                token: $cookies['_csrf_token']
            };

        depositControls.conf['success'] = function(data){
            depositControls.models.amount = null;
            depositControls.models.serial = null;
            messagePrompt.success(data.message);
        }

        $scope.depositControls = depositControls;
        $scope.depositData = depositData;

        requestProxy({keyName: 'getPaymentPlatform'})
            .success(function(data){
                depositData.platformList = data;
                depositData.platform = data[0];
            });
    }]);

})