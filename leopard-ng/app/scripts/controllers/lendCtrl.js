define(['app', 'service'], function (app) {

    'use strict';

    app.controller('lendCtrl', ['financeTools', 'requestProxy', 'messagePrompt'
        , '$scope'
        , function(financeTools, requestProxy, messagePrompt, $scope){

        var lendApplyControls = {
            conf: {
                keyName: 'lendApply'
            },
            description: {
                label: '项目描述',
                name: 'description',
                require: true
            },
            amount: {
                label: '借款金额',
                name: 'amount',
                pattern: '/^\\d+000$/',
                min: 1000,
                max: 999999999,
                warning: '借款金额必须为1000的倍数',
                require: true
            },
            periods: {
                label: '期数',
                name: 'periods',
                pattern: '/^\\d+$/',
                min: 1,
                require: true
            },
            name: {
                label: '项目名称',
                name: 'name',
                require: true
            },
            rate: {
                label: '年利率',
                name: 'rate',
                pattern: '/^(?:[1-9]\\d*|0)(?:\\.\\d{1})?$/',
                min: 0,
                max: 24.0,
                require: true
            },
            repayMethod: {
                label: '还款方式',
                name: 'repaymentmethod_id'
            },
            guarantee: {
                label: '风险控制方式',
                name: 'guarantee_id'
            },
            type: {
                label: '项目类型',
                name: 'nper_type'
            },
            models: {
                description: null,
                name: null,
                amount: null,
                rate: null,
                periods: null,
                repayMethod: null,
                guarantee: 0,
                type: 100
            },
            repayMethods: [],
            guarantees: [],
            repaymentPlans: []
        }

        lendApplyControls.conf['success'] = function(){
            for(var i in lendApplyControls.models)
                if(i != 'guarantee' && i != 'repayMethod' && i != 'type')
                    lendApplyControls.models[i] = null;

            messagePrompt.success('提交申请书成功, 请耐心等待管理员审核 !');
        }

        $scope.lendApplyControls = lendApplyControls;

        //get repaymethods
        requestProxy({keyName: 'getRepayMethods'})
            .success(function(data){
                lendApplyControls.repayMethods = data;
                lendApplyControls.models.repayMethod = data[0].id;
            });
        //get guarantees
        requestProxy({keyName: 'getGuarantees'})
            .success(function(data){
                lendApplyControls.guarantees = data;
            });

        //toggle the guarantee
        $scope.selectGuarantee = function(id){
            lendApplyControls.models.guarantee = id;
        }
        //set a function to generate repayment plan
        $scope.generatePlan = function(){
            var models = lendApplyControls.models,
                logic = (function(){
                    var t = lendApplyControls.repayMethods;
                    for(var i in t){
                        if(t[i].id == models.repayMethod)
                            return t[i].logic;
                    }
                })();
            lendApplyControls.repaymentPlans = financeTools
                .getRepaymentPlan(models.rate/(lendApplyControls.models.type == 100?12: 365)
                , models.amount, models.periods, logic);
            $scope.$apply();
        }
        //set a function to upper the amount
        $scope.getUpperAmount = function(){
            var amount = lendApplyControls.models.amount;
            if(/^\d+000$/.test(amount))
                return financeTools.getUpperAmount(amount);
            else
                return '金额无效';
        }
        //set a function to caculation total amount
        $scope.getTotalAmount = function(){
            var models = lendApplyControls.models,
                logic = (function(){
                    var t = lendApplyControls.repayMethods;
                    for(var i in t){
                        if(t[i].id == models.repayMethod)
                            return t[i].logic;
                    }
                })();
            if(models.rate&&models.amount&&models.periods)
                return models.amount + financeTools
                    .getInterest(models.rate/(lendApplyControls.models.type == 100?12: 365)
                    , models.amount, models.periods, logic);
            else
                return 0;
        }

        //set a function to change the configrations for periods
        $scope.changeProjectType = function(){
            if(lendApplyControls.models.type == 100){
                delete lendApplyControls.periods.max;
            }else{
                lendApplyControls.models.repayMethod = 1; //1 is the interest_first repayment method
                lendApplyControls.periods.max = 29;
            }
        }
    }]);

})