define(['ionic', 'truffleController', 'truffleService'], function(){

  'use strict';

  return angular.module('truffleRoute', ['ionic', 'truffleController', 'truffleService'])
    .config(['$stateProvider', '$urlRouterProvider'
      , function($stateProvider, $urlRouterProvider){
        $stateProvider
          .state('truffle', {
            url: '/truffle',
            abstract: true,
            templateUrl: 'views/base.html'
          })
          .state('truffle.home', {
            url: '/home',
            views: {
              'truffle-app': {
                templateUrl: 'views/home.html',
                controller: 'HomeController'
              }
            }
          })
          .state('truffle.activity-wx', {
            url: '/activity-wx',
            views: {
              'truffle-app': {
                templateUrl: 'views/activity-wx.html',
//              controller: 'HomeController'
              }
            }
          })
          .state('truffle.home.notice', {
            url: '/notice/:type',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/notice.html',
                controller: 'PostsController'
              }
            }
          })
          .state('truffle.home.notice.detail', {
            url: '/:id',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/notice_detail.html',
                controller: 'PostController'
              }
            }
          })
          .state('truffle.investment', {
            url: '/investment',
            views: {
              'truffle-app': {
                templateUrl: 'views/investment.html',
                controller: 'InvestmentController'
              }
            }
          })
          .state('truffle.investment.project', {
            url: '/{id:int}',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/project.html',
                controller: 'ProjectController'
              }
            }
          })
          .state('truffle.investment.student', {
            url: '/student',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/investment.html',
                controller: 'InvestmentController'
              }
            }
          })
          .state('truffle.investment.student.project', {
            url: '/{id:int}',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/project_student.html',
                controller: 'ProjectController'
              }
            }
          })
          .state('truffle.lend', {
            url: '/lend',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/lend.html',
                controller: 'StudentApplyController'
              }
            }
          })
          .state('truffle.account', {
            url: '/account',
            resolve: {
              auth: ['checkPermission', function(checkPermission){
                return checkPermission();
              }]
            },
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account.html',
                controller: 'AccountController'
              }
            }
          })
          .state('truffle.account.password', {
            url: '/password',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/password.html',
                controller: 'PasswordController'
              }
            }
          })
          .state('truffle.account.bankcard', {
            url: '/bankcard',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/bankcard.html',
                controller: 'BankcardController'
              }
            }
          })
          .state('truffle.account.invitation', {
            url: '/invitation',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/invitation.html',
                controller: 'AccountController'
              }
            }
          })
          .state('truffle.account.student_apply', {
            url: '/student_apply',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/student_apply.html',
                controller: 'StudentApplyLogsController'
              }
            }
          })
          .state('truffle.account.logs', {
            url: '/logs',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/logs.html'
              }
            }
          })
          .state('truffle.account.logs.investment', {
            url: '/investment',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/logs_investment.html',
                controller: 'LogsController'
              }
            }
          })
          .state('truffle.account.logs.lending', {
            url: '/lending',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/logs_lending.html',
                controller: 'LogsController'
              }
            }
          })
          .state('truffle.account.logs.deposit', {
            url: '/deposit',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/logs_deposit.html',
                controller: 'LogsController'
              }
            }
          })
          .state('truffle.account.logs.withdraw', {
            url: '/withdraw',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/logs_withdraw.html',
                controller: 'LogsController'
              }
            }
          })
          .state('truffle.account.logs.fund', {
            url: '/fund',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/logs_fund.html',
                controller: 'LogsController'
              }
            }
          })
          .state('truffle.account.redPacket', {
            url: '/red-packet',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/red_packet.html',
                controller: 'RedPacketController'
              }
            }
          })
          .state('truffle.account.automatic', {
            url: '/automatic',
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/automatic.html',
                controller: 'AutomaticController'
              }
            }
          })
          .state('truffle.account.recharge', {
            url: '/recharge',
            cache: true,
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/recharge.html',
                controller: 'RechargeController'
              }
            }
          })
          .state('truffle.account.withdraw', {
            url: '/withdraw',
            cache: true,
            views: {
              'truffle-app@truffle': {
                templateUrl: 'views/account/withdraw.html',
                controller: 'WithdrawController'
              }
            }
          })
          .state('truffle.register', {
            url: '/register',
            views: {
              'truffle-app': {
                templateUrl: 'views/register.html',
                controller: 'RegisterController'
              }
            }
          });
        $urlRouterProvider.otherwise('/truffle/home');
    }]);
});
