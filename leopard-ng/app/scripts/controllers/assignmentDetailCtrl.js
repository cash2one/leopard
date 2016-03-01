define(['app', 'service'], function (app) {

    'use strict';

    app.controller('assignmentDetailCtrl', ['configFactory', 'financeTools'
        , 'requestProxy', 'messagePrompt', '$scope', '$routeParams', '$modal'
        , '$location', '$rootScope', '$sce'
        , function(configFactory, financeTools, requestProxy, messagePrompt, $scope
            , $routeParams, $modal, $location, $rootScope, $sce){

        var projectDetailControls = {
                conf: {
                    //select config
                    keyName: 'buyAssignment'
                },
                investAmount: null,
                models: {
                    investAmount: null
                }
            },
            assignment = {
                info: {},
                repaymentPlans: [],
                user: {},
                project: {},
                isInvest: false,
                isStudent: false
            },
            investModal = null,
            //read config
            getProjectConf = configFactory(
                ['getAssignment'],
                {params: {project_id: $routeParams['id'],
                investment_id: $routeParams['id']}}
            );

        //set submit function
        projectDetailControls.conf['fun'] = openModal;

        $scope.projectDetailControls = projectDetailControls;
        $scope.assignment = assignment;

        function getData(){

            //get project information
            requestProxy(getProjectConf)
                .success(function(data){
                    assignment.info = data;
                    assignment.project = data.project;

                    //set some attributes when the project was assignment
                    projectDetailControls.models.investAmount = data.amount;

                    assignment.info.discount = data.discount || 0;
                    assignment.info.invest_award = data.project.invest_award;

                    assignment.info.invest_award = assignment.info.invest_award * 100;

                    assignment.info.guaranty = $sce.trustAsHtml(assignment.info.guaranty);

                    //caculation the repayment plans
                    assignment.repaymentPlans = financeTools.getRepaymentPlan(data.rate, data.amount,
                        data.periods, data.project.repaymentmethod.logic);
                })
                .error(function(){
                    $location.path('/404');
                });

            //get user's information
            if($scope.CURRENT_USER_ID)
                requestProxy({keyName: 'getUser'})
                    .success(function(data){
                        assignment.user = data;
                    });
        }
        getData();

        // watch the user id to get user information
        $scope.$watch('CURRENT_USER_ID', function (id) {
            if(id){
                requestProxy({keyName: 'getUser'})
                    .success(function(data){
                        assignment.user = data;
                    });
            }else{
                assignment.user = {};
            }
        })

        //set a function to caculation the interest
        $scope.getInterest = function(){
            var t = assignment.info,
                m = projectDetailControls.models.investAmount;
            if(m*1 > assignment.user.available_amount || m*1 > 10000000000)
                return 0;
            if(/^\d+(\.\d{1,2})?$/.test(m))
                return financeTools.getInterest(t.rate, m, t.periods
                    , t.project.repaymentmethod.logic, t.invest_award);
            else
                return 0;
        }

        //set a modal
        $scope.openModal = openModal;
        function openModal(){
            if(!$scope.CURRENT_USER_ID){
                $location.path('/login');
                messagePrompt.forbidden('请先登录后再进行投资 !');
                return;
            }
            var m = projectDetailControls.models.investAmount,
                repaymentPlans = financeTools.getRepaymentPlan(assignment.project.rate
                , m, assignment.project.periods, assignment.project.repaymentmethod.logic);

            var temp = financeTools.getInterest(assignment.project.rate
                , m, assignment.project.periods, assignment.project.repaymentmethod.logic
                , assignment.project.invest_award);

            repaymentPlans.push({
                periods: null,
                monthInterest: temp + m*1,
                monthAmount: m,
                interest: temp,
                amount: null
            });

            if(investModal){
                investModal.close();
            }

            investModal = $modal.open({
                templateUrl: 'invest_project_modal.html',
                controller: ['$scope', '$modalInstance', 'getData'
            , 'assignment', 'plans', 'resetAmount', 'config', 'messagePrompt', 'configFactory', 'requestProxy'
            , investModalIns],
                resolve: {
                    getData: function () {
                        return getData;
                    },
                    assignment: function(){
                        return {
                            info: assignment.info,
                            amount: m,
                            isInvest: assignment.isInvest
                        };
                    },
                    plans: function(){
                        return repaymentPlans;
                    },
                    resetAmount: function(){
                        return function(){projectDetailControls.models.investAmount = null};
                    }
                }
            });
        }
        //set a modal controller
        var investModalIns = function($scope, $modalInstance, getData
            , project, plans, resetAmount, config, messagePrompt, configFactory, requestProxy){

            var invest = {
                    tradePass: null,
                    amountType: 1,
                    projectPass: null,
                    config: config['platformConfig']['tradePass']['invest']
                },
                investConfig = configFactory(['buyAssignment']
                    , {params: {project_id: assignment.info.id,
                        investment_id: assignment.info.id}});

            $scope.assignment = assignment;
            $scope.plans = plans;
            $scope.invest = invest;

            $scope.ok = function () {
                if(invest.config && !invest.tradePass){
                    messagePrompt.forbidden('请先输入交易密码 !');
                    return;
                }
                if(assignment.info.has_password && !invest.projectPass){
                    messagePrompt.forbidden('请先输入定向密码 !');
                    return;
                }
                //invest project
                investConfig.data = {
                    amount: assignment.amount,
                    trade_password: invest.tradePass,
                    capital_deduct_order: invest.amountType,
                    password: invest.projectPass
                }
                if(invest.packet)
                    investConfig.data.redpacket_id = invest.packet;
                requestProxy(investConfig)
                    .success(function(data){
                        messagePrompt.success(data.message);
                        getData();
                        resetAmount();
                        $modalInstance.close();
                    });
                invest.tradePass = null;
            };
            $scope.cancel = function () {
                $modalInstance.dismiss();
                invest.tradePass = null;
            };
        };
    }]);

})
