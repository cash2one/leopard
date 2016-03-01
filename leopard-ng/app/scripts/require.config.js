requirejs.config({

    baseUrl: '/',
    waitSeconds: 15,
    paths: {
        //Library
        'jquery': 'bower_components/jquery/jquery.min',
        'angular': 'bower_components/angular/angular',
        'angularRoute': 'bower_components/angular-route/angular-route.min',
        'angularCookie': 'bower_components/angular-cookies/angular-cookies.min',
        'ui.bootstrap': 'scripts/lib/ui-bootstrap-tpls',
        'morris': 'bower_components/morris.js/morris.min',
        'raphael': 'bower_components/raphael/raphael-min',
        'zeroclip': 'bower_components/zeroclipboard/ZeroClipboard.min',
        'fancybox': 'bower_components/fancybox/source/jquery.fancybox.pack',
        //Controller
        'baseCtrl': 'scripts/controllers/baseCtrl',
        'accountCtrl': 'scripts/controllers/accountCtrl',
        'loginCtrl': 'scripts/controllers/loginCtrl',
        'homeCtrl': 'scripts/controllers/homeCtrl',
        'investmentCtrl': 'scripts/controllers/investmentCtrl',
        'investListCtrl': 'scripts/controllers/investListCtrl',

        'assignmentCtrl': 'scripts/controllers/assignmentCtrl',
        'assignmentDetailCtrl': 'scripts/controllers/assignmentDetailCtrl',

        'simpleListCtrl': 'scripts/controllers/simpleListCtrl',
        'redPacketCtrl': 'scripts/controllers/redPacketCtrl',
        'profileCtrl': 'scripts/controllers/profileCtrl',
        'lendCtrl': 'scripts/controllers/lendCtrl',
        'projectDetailCtrl': 'scripts/controllers/projectDetailCtrl',
        'registerCtrl': 'scripts/controllers/registerCtrl',
        'bankcardCtrl': 'scripts/controllers/bankcardCtrl',
        'autoInvestCtrl': 'scripts/controllers/autoInvestCtrl',
        'withdrawCtrl': 'scripts/controllers/withdrawCtrl',
        'depositCtrl': 'scripts/controllers/depositCtrl',
        'vipCtrl': 'scripts/controllers/vipCtrl',
        'postCtrl': 'scripts/controllers/postCtrl',
        'forgetCtrl': 'scripts/controllers/forgetCtrl',
        'guaranteeCtrl': 'scripts/controllers/guaranteeCtrl',
        'messageCtrl': 'scripts/controllers/messageCtrl',
        'rankCtrl': 'scripts/controllers/rankCtrl',
        'contractCtrl': 'scripts/controllers/contractCtrl',
        'transferContractCtrl': 'scripts/controllers/transferContractCtrl',
        'assigneeContractCtrl': 'scripts/controllers/assigneeContractCtrl',
        'repaymentCtrl': 'scripts/controllers/repaymentCtrl',
        'finrepaymentCtrl': 'scripts/controllers/finrepaymentCtrl',
        'borrowingCtrl': 'scripts/controllers/borrowingCtrl',
        'withdrawListCtrl': 'scripts/controllers/withdrawListCtrl',
        'lendStudentCtrl': 'scripts/controllers/lendStudentCtrl',
        'studentApplyCtrl': 'scripts/controllers/studentApplyCtrl',
        'studentRepaymentCtrl': 'scripts/controllers/studentRepaymentCtrl',
        'queryListCtrl': 'scripts/controllers/queryListCtrl',
        'commodityListCtrl': 'scripts/controllers/commodityListCtrl',
        'commodityDetailsCtrl': 'scripts/controllers/commodityDetailsCtrl',
        'originalDetailCtrl': 'scripts/controllers/originalDetailCtrl',
        //module, config, router, directive, service
        'app': 'scripts/app',
        'config': 'scripts/config',
        'routes': 'scripts/routes',
        'directive': 'scripts/directive',
        'service': 'scripts/service',
        //activate
        'christmas': 'scripts/christmas',
        'snow': 'scripts/lib/snow'
    },

    shim: {
        'jquery': {
            exports: 'jQuery'
        },
        'angular': {
            deps: [ 'jquery' ],
            exports: 'angular'
        },
        'angularRoute': {
            deps: [ 'angular' ]
        },
        'angularCookie': {
            deps: [ 'angular' ]
        },
        'ui.bootstrap': {
            deps: [ 'angular' ]
        },
        'morris': {
            deps: [ 'jquery', 'raphael' ],
            exports: 'morris'
        },
        'fancybox': {
            deps: [ 'jquery' ],
            exports: 'fancybox'
        }
    }
});


require([

    'angular',
    'config',
    'routes',
    'directive',
    'service',
    'christmas'

], function(angular) {

    'use strict';

    angular.bootstrap(document, ['leopard']);
});
