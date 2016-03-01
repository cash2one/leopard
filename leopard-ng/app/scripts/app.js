define(['angular', 'angularRoute', 'ui.bootstrap', 'config'], function (angular) {

    'use strict';

    return angular.module('leopard', ['ngRoute', 'ui.bootstrap', 'ngCookies'])
        .run(['$timeout', '$document', function($timeout, $document){
            //show body when document ready
            $timeout(function(){
                jQuery($document[0].body).fadeIn();
            }, 1);
        }])
        //set the tooltip of ui-bootstrap
        .config(['$tooltipProvider', function($tooltipProvider){
            $tooltipProvider.options({
                popupDelay: 100,
                appendToBody: true
            });
        }])
        //set the csrf token
        .config(['$httpProvider', function($httpProvider) {
            $httpProvider.defaults.xsrfCookieName = '_csrf_token';
            $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
        }])
        .config(['$compileProvider', function ($compileProvider) {
            $compileProvider.aHrefSanitizationWhitelist(/^(http|javascript\:\;)/);
        }])
        .filter('statusFilter', ['config', function(config){
            return function(input ,type){
                var s = config['statusConfig'][type];
                if(s)
                    return s[input];
                else
                    return '\u672A\u77E5\u72B6\u6001'; //return '未知状态'
            }
        }])
        .filter('periodsFilter', ['config', function(config){
            return function(input ,t){
                if(t == 1)
                    return '1/1';
                else if(input + 1 == t)
                    return input + '/' + t;
                else if(input + 1 < t)
                    return (input + 1) + '/' + t;
                else if(input == t)
                    return t + '/' + t;
            }
        }]);
});
