define(['app', 'service'], function (app) {

    'use strict';

    app.controller('projectDetailCtrl', ['configFactory', 'financeTools'
        , 'requestProxy', 'messagePrompt', '$scope', '$routeParams', '$modal'
        , '$location', '$rootScope', '$sce', '$interval'
        , function(configFactory, financeTools, requestProxy, messagePrompt, $scope
            , $routeParams, $modal, $location, $rootScope, $sce, $interval){

        var projectDetailControls = {
                conf: {
                    //select config
                    keyName: 'investProject'
                },
                investAmount: null,
                models: {
                    investAmount: null
                }
            },
            project = {
                info: {},
                repaymentPlans: [],
                user: {},
                isInvest: $location.path().indexOf('invest')!=-1,
                isStudent: $location.path().indexOf('student')!=-1
            },
            investModal = null,
            remainTime = 0,
            //read config
            getProjectConf = configFactory([project.isInvest?
                project.isStudent?'getStudentProject': 'getProject': 'getAssignment'],
                {params: {project_id: $routeParams['id'],
                investment_id: $routeParams['id']}});

        var getTenderRedpacketConf = configFactory(
                ['getTenderRedPacket'], {params: {}}
            );

        //set submit function
        projectDetailControls.conf['fun'] = openModal;


        $scope.remainDate = {
            day: '000',
            hour: '00',
            minute: '00',
            second: '00'
        };

        // 进入倒计时
        function launch() {
            var timer = $interval(function(){
                if(updateTime() == 0) {
                    $interval.cancel(timer);
                }
            }, 1000);
            updateTime();
            
        };

        // /**
        //  * 更新倒计时时间
        //  */
        function updateTime () {
            var time = countDown($scope.remainTime);
            if(time != 0) {
                $scope.remainDate.day = time.day;
                $scope.remainDate.hour = time.hour;
                $scope.remainDate.minute = time.minute;
                $scope.remainDate.second = time.second;
                $scope.remainTime -= 1;
                return 1;
            } else {
                return 0;
            }
        };

        function countDown (iRemain) {
        
            var dateNow = new Date();

        //     // 如果时间不足够倒计时，退出并返回0
        //     // 否则返回剩余时间
            if(iRemain <= 0) {
                return 0;
            } else {
                var endDate = {};
                endDate.day = fillZero(iRemain / 86400, 3);
                iRemain %= 86400;

                endDate.hour = fillZero(iRemain / 3600, 2);
                iRemain %= 3600;

                endDate.minute = fillZero(iRemain / 60, 2);
                iRemain %= 60;

                endDate.second = fillZero(iRemain, 2);

                return endDate;
            }
        };

        function fillZero (num, digit) {
            var str = '' + parseInt(num);
            while(digit > str.length) {
                str = '0' + str;
            }

            return str;
        };

        $scope.projectDetailControls = projectDetailControls;
        $scope.project = project;
        $scope.remainTime = remainTime;

        function getData(){

            //get project information
            requestProxy(getProjectConf)
                .success(function(data){
                    project.info = data;
                    project.project_info = data['project'];
                    if (data.remain_bid_time){
                        $scope.remainTime = data.remain_bid_time;
                        launch();
                    }

                    //produce the amount config
                    projectDetailControls.investAmount = {
                        label: '投资金额',
                        name: 'invest_amount',
                        pattern: project.isStudent?'/^\\d+00$/': '/^\\d+(\\.\\d{1,2})?$/',
                        min: Math.floor((data.min_lend_amount>(data.amount*100 - data.borrowed_amount*100)/100
                            ?(data.amount*100 - data.borrowed_amount*100)/100: data.min_lend_amount)*100)/100,
                        // max: Math.floor((data.max_lend_amount>(data.amount*100 - data.borrowed_amount*100)/100
                            // ?(data.amount*100 - data.borrowed_a/mount*100)/100: data.max_lend_amount)*100)/100,
                        warning: project.isStudent?'投资金额必须为100的整数倍': null,
                        require: true
                    }
                    if(project.info.filter_risk_controls){
                        for (var i = 0; i < project.info.filter_risk_controls.length; i++) {
                            project.info.filter_risk_controls[i].content = $sce.trustAsHtml(project.info.filter_risk_controls[i].content);
                        }
                    }
                    project.info.invest_award = project.info.invest_award * 100;

                    project.info.guaranty = $sce.trustAsHtml(project.info.guaranty);

                    //caculation the repayment plans
                    project.repaymentPlans = financeTools.getRepaymentPlan(data.rate, data.amount,
                        data.periods, data.repaymentmethod.logic);
                })
                .error(function(){
                    $location.path('/404');
                });

            //get user's information
            if($scope.CURRENT_USER_ID)
                requestProxy({keyName: 'getUser'})
                    .success(function(data){
                        project.user = data;
                    });
        }
        getData();

        // watch the user id to get user information
        $scope.$watch('CURRENT_USER_ID', function (id) {
            if(id){
                requestProxy({keyName: 'getUser'})
                    .success(function(data){
                        project.user = data;
                    });
            }else{
                project.user = {};
            }
        })

        //set a function to caculation the interest
        $scope.getInterest = function(){
            var t = project.info,
                m = projectDetailControls.models.investAmount;
            if(m*1 > project.user.available_amount || m*1 > 10000000000)
                return 0;
            if(/^\d+(\.\d{1,2})?$/.test(m))
                return financeTools.getInterest(t.rate, m, t.periods
                    , t.repaymentmethod.logic, t.invest_award);
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
                repaymentPlans = financeTools.getRepaymentPlan(project.info.rate
                , m, project.info.periods, project.info.repaymentmethod.logic);

            var temp = financeTools.getInterest(project.info.rate
                , m, project.info.periods, project.info.repaymentmethod.logic
                , project.info.invest_award);

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
            , 'project', 'plans', 'resetAmount', 'config', 'messagePrompt', 'configFactory', 'requestProxy', 'tenderRedpackets'
            , investModalIns],
                resolve: {
                    getData: function () {
                        return getData;
                    },
                    project: function(){
                        return {
                            info: project.info,
                            amount: m,
                            isInvest: project.isInvest
                        };
                    },
                    tenderRedpackets: function(){
                        getTenderRedpacketConf.params['tender_amount'] = parseInt(m);
                        return requestProxy(getTenderRedpacketConf);
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
            , project, plans, resetAmount, config, messagePrompt, configFactory, requestProxy, tenderRedpackets){

            tenderRedpackets = tenderRedpackets.data;

            var invest = {
                    tradePass: null,
                    amountType: 1,
                    projectPass: null,
                    config: config['platformConfig']['tradePass']['invest'],
                    packet: tenderRedpackets.length?tenderRedpackets[0].id: null
                },
                investConfig = configFactory([project.isInvest?
                    'investProject': 'buyAssignment']
                    , {params: {project_id: project.info.id,
                        investment_id: project.info.id}});

            $scope.project = project;
            $scope.plans = plans;
            $scope.invest = invest;
            $scope.tenderRedpackets = tenderRedpackets;

            $scope.ok = function () {
                if(invest.config && !invest.tradePass){
                    messagePrompt.forbidden('请先输入交易密码 !');
                    return;
                }
                if(project.info.has_password && !invest.projectPass){
                    messagePrompt.forbidden('请先输入定向密码 !');
                    return;
                }
                //invest project
                investConfig.data = {
                    amount: project.amount,
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
