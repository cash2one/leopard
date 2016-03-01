define(['app', 'service', 'config'], function (app) {

    'use strict';

    app.controller('autoInvestCtrl', ['requestProxy', 'messagePrompt'
        , 'configFactory', 'config', '$scope', '$modal'
        , function(requestProxy, messagePrompt, configFactory, config, $scope
            , $modal){
            var formControls = {
                    conf: {
                        keyName: 'setAutoInvest' //this is the config's name in 'config'
                    },
                    isOpen: {
                        label: '是否启用',
                        name: 'is_open'
                    },
                    maxAmount: {
                        label: '最大投资额',
                        name: 'max_amount',
                        pattern: '/^\\d+(\\.\\d{1,2})?$/',
                        max: 100000,
                        min: 100,
                        require: true
                    },
                    minAmount: {
                        label: '最小投资额',
                        name: 'min_amount',
                        pattern: '/^\\d+(\\.\\d{1,2})?$/',
                        min: 100,
                        require: true
                    },
                    maxRate: {
                        label: '最大利率',
                        name: 'max_rate',
                        pattern: '/^(?!0+(?:\\.0+)?$)(?:[1-9]\\d*|0)(?:\\.\\d{1})?$/',
                        min: 0.1,
                        max: 24.0,
                        require: true
                    },
                    minRate: {
                        label: '最小利率',
                        name: 'min_rate',
                        pattern: '/^(?!0+(?:\\.0+)?$)(?:[1-9]\\d*|0)(?:\\.\\d{1})?$/',
                        min: 0.1,
                        max: 24.0,
                        require: true
                    },
                    maxPeriods: {
                        label: '最大期数',
                        name: 'max_periods',
                        pattern: '/^\\d+$/',
                        min: 1,
                        require: true
                    },
                    minPeriods: {
                        label: '最小期数',
                        name: 'min_periods',
                        pattern: '/^\\d+$/',
                        min: 1,
                        require: true
                    },
                    reserveAmount: {
                        label: '账户预留金额',
                        name: 'reserve_amount',
                        require: true
                    },
                    tradePass: {
                        label: '交易密码',
                        name: 'trade_password',
                        require: true
                    },
                    models: {}
                };
            //set the callback function
            formControls.conf['success'] = function(){
                formControls.models.trade_password = null;
                messagePrompt.success('设置自动投标成功 !');
            }

            $scope.formControls = formControls;

            //get bankcard data
            function getData(){
                requestProxy({keyName: 'getAutoInvest'})
                    .success(function(data){
                        formControls.models = data;
                        formControls.maxAmount.max = data.max_allow_amount;
                        $scope.togglePower(true);
                    });
            }
            getData();

            //set a function to change the auto invest
            $scope.togglePower = function(onlySet){
                if(!onlySet)
                    formControls.models.is_open = !formControls.models.is_open;
                for(var i in formControls)
                    if(i != 'conf' && i != 'models' && i != 'isOpen' && i != 'tradePass')
                        formControls[i].require = formControls.models.is_open;
            }
    }]);
})