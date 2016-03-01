define(['ionic', 'truffleConfig'], function(){

  'use strict';

  return angular.module('truffleService', ['truffleConfig'])
    /**
     * add mobile interceptor into the http provider
     * @date        2015-3-28
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .config(['$httpProvider', function ($httpProvider) {
      $httpProvider.interceptors.push('mobileHttpInterceptor');
    }])
    /**
     * request handler
     * @date        2015-3-28
     * @author      Peach<scdzwyxst@gmail.com>
     * @param  request config
     */
    .factory('requestHandler', ['localStorageService', 'messagePrompt', 'config', '$http'
      , '$ionicLoading', '$log', '$rootScope', '$state', '$timeout'
      , function(localStorageService, messagePrompt, config, $http, $ionicLoading, $log
        , $rootScope, $state, $timeout){
      return function(arg){
        var conf = {
          method: 'GET', // set default method,
          headers: {
            Platform: 'wechat',
            withCredentials: true
          }
        };

        if(angular.isString(arg)){
          conf.keyName = arg;
        }else{
          var temp = {};
          angular.copy(arg, temp);
          angular.extend(conf, temp);
        }

        // extend api configration
        if(conf.keyName){
          if(typeof(config.apis[conf.keyName]) == 'string')
            conf.url = config.apis[conf.keyName];
          else
            angular.extend(conf, config.apis[conf.keyName]);

          // add base url from apis config
          conf.url = config.apis.baseUrl + conf.url;

          delete conf.keyName;
        }

        // check config
        if(!conf.url)
          return console.error('Missing url in the request config!');
        if(!conf.method)
          return console.error('Missing method in the request config!');

        // splice url if the url has params
        if(conf.url.indexOf('/:') != -1){
          (function(){
            // http://baidu.com/:id/action/:user/:title
            var temp = conf.url.split('/:');
            for(var i = 1;i<temp.length;i++){
              var param = temp[i].split('/'),
                  repaceKey = param[0];

              // find param in the params field of config
              if(conf.params[repaceKey]){
                param[0] = conf.params[repaceKey];
                temp[i] = param.join('/');
                delete conf.params[repaceKey];
              }else
                return console.error('Missing param: ' + param[0] + ' in the request config!');
            }

            conf.url = temp.join('/');
          })()
        }

        // add base url from conf
        if(conf.baseUrl){
          conf.url = conf.baseUrl + conf.url;
          delete conf.baseUrl;
        }

        // if localstorage have the auth key, add it
        if(localStorageService.get('bearer_token')){
          angular.extend(conf.headers
            , {'Authorization': 'Bearer ' + localStorageService.get('bearer_token')});
        }

        // create http request
        var req = $http(conf);

        // handle all error message in global
        req.error(function(data, status){
          if(status == 403 || status == 401){
            $rootScope.CURRENT_USER_ID = null;
            localStorageService.remove('CURRENT_USER_ID');
            $state.go('truffle.home');
            $timeout(function(){
              $state.go('truffle.account');
            }, 1);
          }
          messagePrompt.error((data?data.message: null) || '啊哦，网络请求出错咧！');
          // hide the loading if some loading has been shown
          $ionicLoading.hide();
        });

        // handle all success message in global
        req.success(function (data) {
          data && data.message && messagePrompt.success(data.message);
          $log.debug('Response - ', data);
        });

        return req;
      }
    }])
    /**
     * request interceptor
     * @date        2015-3-28
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .factory('mobileHttpInterceptor', ['$q', '$log', function ($q, $log) {
      return {
        response: function(response){
          var fakeStatus = response.data?response.data.code: 0;

          if(response.data && response.data.results)
            response.data = response.data.results;

          if(fakeStatus >= 400){
            response.status = fakeStatus;

            $log.debug('Intercept an fake error - ', response.data);

            return $q.reject(response);
          }

          return response;
        }
      }
    }])
    /**
     * login modal service
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .factory('loginService', ['localStorageService', 'requestHandler', '$ionicModal'
      , '$rootScope', '$q', '$state'
      , function(localStorageService, requestHandler, $ionicModal, $rootScope, $q, $state){
      return {
        openModal: function(){
          var current_date = (new Date()).getTime();
          var $scope = $rootScope.$new(true),
              formControls = {
                conf: {
                  keyName: 'login'
                },
                username: {
                  label: '用户名',
                  name: 'username',
                  require: true
                },
                password: {
                  label: '密码',
                  name: 'password',
                  require: true
                },
                vercode: {
                    label: '验证码',
                    name: 'identifying_code',
                    require: true
                },
                cb: {
                  label: '随机串',
                  name: 'cb',
                  require: true
                },
                models: {
                  username: null,
                  password: null,
                  vercode: null,
                  current_date: current_date,
                  cb: current_date
                }
              },
              deferred = $q.defer();

          formControls.conf['success'] = function(data){
            $rootScope.CURRENT_USER_ID = data.user_id;
            localStorageService.set('CURRENT_USER_ID', data.user_id);
            localStorageService.set('bearer_token', data.token);

            $scope.modal.hide();
            $scope.$destroy();
            deferred.resolve();
          }
          formControls.conf['error'] = function () {
            formControls.models.password = null;
          }

          $scope.reload_vcode = function reload_vcode(){
            var current_date = (new Date()).getTime();
            formControls.models.current_date = current_date;
            formControls.models.cb = current_date;
          }

          $scope.formControls = formControls;

          $ionicModal.fromTemplateUrl('/views/login.html', {
            scope: $scope
          }).then(function(modal){
            $scope.modal = modal;
            modal.show();
          })

          $scope.$on('$destroy', function(){
            $scope.modal.remove();
          })

          $scope.$on('modal.hidden', function(){
            if(!$rootScope.CURRENT_USER_ID)
              deferred.reject();
          });

          return deferred.promise;
        },
        logout: function(){
          delete $rootScope.CURRENT_USER_ID;
          localStorageService.remove('CURRENT_USER_ID');
          localStorageService.remove('bearer_token');
          $state.transitionTo('truffle.home');
        }
      }
    }])
    /**
     * message prompt service
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .factory('messagePrompt', ['$timeout', '$ionicLoading', '$ionicPopup'
      , function($timeout, $ionicLoading, $ionicPopup){
      function alertMessage(message, type){
        return $ionicPopup.alert({
          title: '\u7CFB\u7EDF\u63D0\u793A', //系统提示
          template: message,
          okText: '\u786E\u5B9A',
          okType: 'button-' + type
        });
      }
      return {
        success: function(message){
          return alertMessage(message, 'balanced');
        },
        error: function(message){
          return alertMessage(message, 'assertive');
        },
        info: function(message){
          return alertMessage(message, 'positive');
        },
        tooltip: function(message){
          message += '';
          if(!message)
            return;
          $ionicLoading.show({
            template: message,
            noBackdrop: true
          });

          $timeout(function(){
            $ionicLoading.hide();
          }, message.length*80 < 1500?1500: message.length*80);
        }
      }
    }])
    /**
     * check permission service
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .factory('checkPermission', ['loginService', 'localStorageService', '$rootScope'
      , '$q', '$state', '$timeout'
      , function(loginService, localStorageService, $rootScope, $q, $state, $timeout){
      return function(){
        var deferred = $q.defer();

        $timeout(function () {
          if($rootScope.CURRENT_USER_ID)
            deferred.resolve();
          else if(localStorageService.get('CURRENT_USER_ID')){
            $rootScope.CURRENT_USER_ID = localStorageService.get('CURRENT_USER_ID');
            deferred.resolve();
          }else{
            loginService.openModal().then(function(){
              deferred.resolve();
            }, function(){
              deferred.reject();
              $state.reload();
            });
          }
        }, 1)

        return deferred.promise;
      }
    }])
})
