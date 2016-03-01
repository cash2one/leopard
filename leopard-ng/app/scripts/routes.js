define(['app', 'service', 'accountCtrl', 'baseCtrl', 'loginCtrl'
    , 'homeCtrl', 'investmentCtrl', 'investListCtrl', 'simpleListCtrl'
    , 'assignmentCtrl', 'assignmentDetailCtrl', 'bankcardCtrl'
    , 'redPacketCtrl', 'profileCtrl', 'lendCtrl', 'projectDetailCtrl', 'registerCtrl'
    , 'bankcardCtrl', 'autoInvestCtrl', 'withdrawCtrl', 'vipCtrl', 'postCtrl'
    , 'forgetCtrl', 'guaranteeCtrl', 'messageCtrl', 'depositCtrl', 'rankCtrl'
    , 'contractCtrl', 'transferContractCtrl', 'assigneeContractCtrl', 'repaymentCtrl'
    , 'finrepaymentCtrl', 'borrowingCtrl', 'commodityListCtrl','commodityDetailsCtrl'
    , 'withdrawListCtrl', 'lendStudentCtrl', 'originalDetailCtrl'
    , 'studentRepaymentCtrl', 'queryListCtrl']
    , function (app) {

    'use strict';

    app.config(['$locationProvider', '$routeProvider', function ($locationProvider, $routeProvider) {

        $routeProvider.
            when('/', {
                templateUrl: '/views/home.html',
                controller: 'homeCtrl'
            }).
            when('/invest', {
                templateUrl: '/views/invest.html',
                controller: 'investListCtrl'
            }).
            when('/invest/student', {
                templateUrl: '/views/invest.html',
                controller: 'investListCtrl'
            }).
            when('/invest/:id', {
                templateUrl: '/views/project_detail.html',
                controller: 'projectDetailCtrl'
            }).
            when('/original/:id', {
                templateUrl: '/views/original_project.html',
                controller: 'originalDetailCtrl'
            }).
            when('/invest/student/:id', {
                templateUrl: '/views/invest_dream.html',
                controller: 'projectDetailCtrl'
            }).
            when('/invest-dream', {
                templateUrl: '/views/invest_dream.html',
            }).
            when('/assignment', {
                templateUrl: '/views/assignment.html',
                controller: 'assignmentCtrl'
            }).
            when('/assignment/:id', {
                templateUrl: '/views/assignment_detail.html',
                controller: 'assignmentDetailCtrl'
            }).
            when('/lend', {
                templateUrl: '/views/lend.html',
            }).
            when('/apply', {
                templateUrl: '/views/apply.html',
                controller: 'lendCtrl'
            }).
            when('/student-apply', {
                templateUrl: '/views/student_apply.html',
                controller: 'lendStudentCtrl'
            }).
            when('/affiliate', {
                templateUrl: '/views/post/affiliate.html'
            }).
            when('/account', {
                templateUrl: '/views/account/index.html',
                controller: 'accountCtrl',
                resolve: {
                    check: ['checkPermission', function(checkPermission){
                        return checkPermission();
                    }]
                }
            }).
            when('/account/:category', {
                templateUrl: '/views/account/index.html',
                controller: 'accountCtrl',
                resolve: {
                    check: ['checkPermission', function(checkPermission){
                        return checkPermission();
                    }]
                }
            }).
            when('/account/:category/:view', {
                templateUrl: '/views/account/index.html',
                controller: 'accountCtrl',
                resolve: {
                    check: ['checkPermission', function(checkPermission){
                        return checkPermission();
                    }]
                }
            }).
            when('/post/:category/:type', {
                templateUrl: '/views/post/index.html',
                controller: 'postCtrl'
            }).
            when('/post/:category/:type/:id', {
                templateUrl: '/views/post/index.html',
                controller: 'postCtrl'
            }).
            when('/login', {
                reloadOnSearch: false,
                templateUrl: '/views/login.html',
                controller: 'loginCtrl'
            }).
            when('/forget', {
                templateUrl: '/views/forget.html',
                controller: 'forgetCtrl'
            }).
            when('/upgrade', {
                templateUrl: '/views/upgrade.html',
                controller: 'forgetCtrl'
            }).
            when('/register', {
                templateUrl: '/views/register.html',
                controller: 'registerCtrl'
            }).
             when('/generalize', {
                templateUrl: '/views/generalize_register.html',
                controller: 'registerCtrl'
            }).
            when('/forget-password', {
                templateUrl: '/views/forget_password.html'
            }).
            when('/guarantee_info/:id', {
                templateUrl: '/views/guarantee.html',
                controller: 'guaranteeCtrl'
            }).
            when('/security', {
                templateUrl: '/views/post/security.html'
            }).
            when('/repo', {
                templateUrl: '/views/post/repo.html'
            }).
            when('/mechanism', {
                templateUrl: '/views/post/mechanism.html'
            }).
            when('/claim', {
                templateUrl: '/views/post/claim.html'
            }).
            when('/experience', {
                templateUrl: '/views/post/experience.html'
            }).
            when('/indemnify', {
                templateUrl: '/views/post/indemnify.html'
            }).
            when('/bao-li-feng', {
                templateUrl: '/views/post/bao_li_feng.html'
            }).
            when('/april-events', {
                templateUrl: '/views/post/april_events.html'
            }).
            when('/may-events', {
                templateUrl: '/views/post/may_events.html'
            }).
            when('/june-events', {
                templateUrl: '/views/post/june_events.html'
            }).
            when('/assignee_contract/:id', {
                templateUrl: '/views/transfer_contract.html',
                controller: 'assigneeContractCtrl'
            }).
            when('/transfer_contract/:id', {
                templateUrl: '/views/transfer_contract.html',
                controller: 'transferContractCtrl'
            }).
            when('/contract/:id', {
                templateUrl: '/views/contract.html',
                controller: 'contractCtrl'
            }).
            when('/statements', {
                templateUrl: '/views/statements/statements.html',
            }).
            when('/mall/index', {
                templateUrl: '/views/mall/index.html',
                controller: 'commodityListCtrl'
            }).
            when('/mall/index/:id', {
                templateUrl: '/views/mall/details.html',
                controller: 'commodityDetailsCtrl'
            }).
			when('/newlib',{
				templateUrl:'/views/newlib.html',
			}).
            when('/video',{
                templateUrl:'/views/video.html',
            }).
            when('/ab9161e57ff4dd6cdfd4efc5acc8753d',{  //A5联盟查询接口
                templateUrl:'/views/query.html',
                controller: 'queryListCtrl'
            }).
            otherwise({ templateUrl: '/404.html' });

            //use html5mode
            //$locationProvider.html5Mode(true);
            //use prefix
            $locationProvider.hashPrefix('!');
    }]);
});
