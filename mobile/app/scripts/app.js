define(['ionic', 'truffleRoute', 'truffleDirective', 'ngLocalstorage'], function(){

  'use strict';

  return angular.module('truffleMobile', ['truffleRoute', 'truffleDirective'
    , 'LocalStorageModule'])
    .run(['$rootScope', 'localStorageService', function($rootScope, localStorageService){
      // sync login status from local storage
      $rootScope.CURRENT_USER_ID = localStorageService.get('CURRENT_USER_ID');
    }])
    // set prefix for localstorage
    .config(['localStorageServiceProvider', '$sceDelegateProvider', '$ionicConfigProvider', function(
          localStorageServiceProvider, $sceDelegateProvider, $ionicConfigProvider){
          localStorageServiceProvider.setPrefix('truffle');
          ionic.Platform.isFullScreen = true;
          // 按钮放入下面
          $ionicConfigProvider.tabs.position('bottom');
          // 统一标准样式
          $ionicConfigProvider.tabs.style("standard");
          // 模板缓存数量配置
          $ionicConfigProvider.templates.maxPrefetch(0);
          // 标题中间显示
          $ionicConfigProvider.navBar.alignTitle('center');
          $sceDelegateProvider.resourceUrlWhitelist([
         // Allow same origin resource loads.
          'https://yintong.com.cn/**']);
    }])
    .filter('status', ['config', function(config){
      return function(input ,type){
        var s = config['statusConfig'][type];
        if(s)
          return s[input];
        else
          return '\u672A\u77E5\u72B6\u6001'; //return '未知状态'
      }
    }]);
});
