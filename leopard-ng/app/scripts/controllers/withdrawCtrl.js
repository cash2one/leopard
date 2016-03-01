define(['app', 'service'], function (app) {

    'use strict';

    app.controller('withdrawCtrl', ['financeTools', 'requestProxy', 'messagePrompt'
        , '$scope', '$location', '$timeout'
        , function(financeTools, requestProxy, messagePrompt, $scope, $location, $timeout){

        var withdrawControls = {
            conf: {
                keyName: 'createWithdraw'
            },
            amount: {
                label: '提现金额',
                name: 'amount',
                pattern: '/^\\d+(\\.\\d{1,2})?$/',
                max: $scope.accountData.user.available_amount,
                min: 1,
                require: true
            },
            tradePass: {
                label: '交易密码',
                name: 'trade_password',
                require: true
            },
            phoneCode: {
                label: '短信验证码',
                name: 'phone_code',
                keyName: 'withdrawCode',
                require: true
            },
            bankcard: {
                label: '银行卡',
                name: 'bankcard_id',
                require: true
            },
            amountType: {
                label: '优先选择金额',
                name: 'capital_deduct_order'
            },
            models: {
                amount: null,
                tradePass: null,
                phoneCode: null,
                bankcard: null,
                amountType: 0
            },
            bankcards: []
        },
        bankcardData = {
            bankcardList:null,
            bankcard: null
        };

        withdrawControls.conf['success'] = function(){
            $scope.accountData.user.available_amount -= withdrawControls.models.amount;
            for(var i in withdrawControls.models)
                if(i != 'amountType')
                    withdrawControls.models[i] = null;
            messagePrompt.success('提交提现申请成功, 请耐心等待管理员审核 !');
        }

        $scope.withdrawControls = withdrawControls;
        $scope.bankcardData = bankcardData;

        //set a function to caculation commission
        $scope.getCommission = function(){
            if(withdrawControls.models.amount)
                return Math.ceil(withdrawControls.models.amount/200000)*2;
            else
                return 0;
        }

        //check realname certify
        function check(){
            if(!$scope.accountData.user.username){
                $timeout(check, 100);
                return;
            }
            if(!$scope.accountData.user.realname){
                messagePrompt.forbidden('请先进行实名认证');
                $location.path('account/management/profile');
            }else
                getBankcard();
        }
        check();

        function getBankcard(){
            //get bankcard
            requestProxy({keyName: 'getBankcard'})
                .success(function(data){
                    if(data.length == 0){
                        messagePrompt.forbidden('请先添加银行卡 !');
                        $location.path('/account/management/bankcard');
                        return;
                    }
                    bankcardData.bankcardList = data;
                    bankcardData.bankcard = data[0];
                });
        }
    }]);

})