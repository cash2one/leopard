define(['app', 'service'], function (app) {

    'use strict';

    app.controller('registerCtrl', ['configFactory', 'requestProxy'
        , '$routeParams', '$scope', '$location', '$rootScope', '$window'
        , function(configFactory, requestProxy, $routeParams, $scope
            , $location, $rootScope, $window){

        var formControls = {
                conf: {
                    keyName: 'register' //this is the config's name in 'config'
                },
                username: {
                    label: '用户名',
                    name: 'username',
                    pattern: '/^[a-zA-Z0-9\\u4E00-\\u9FA5]{3,32}$/',
                    warning: '用户名应由3-32位数字、英文或中文组成 !',
                    isExist: 'checkRegisterExist',
                    require: true
                },
                password: {
                    label: '密码',
                    name: 'password',
                    pattern: '/^[a-z][a-z0-9]{7,31}$/i',
                    warning: '登录密码应由8-32位数字、英文组成且首位必须为字母',
                    require: true
                },
                rePassword: {
                    label: '重复密码',
                    name: 'repassword',
                    seemAs: 'password',
                    require: true
                },
                phone: {
                    label: '手机号码',
                    name: 'phone',
                    pattern: '/^[1][1-9][\\d]{9}$/',
                    keyName: 'registerCode',
                    require: true
                },
                phoneCode: {
                    label: '短信验证码',
                    name: 'phone_code',
                    require: true
                },
                inviteUser: {
                    label: '邀请人',
                    name: 'friend_invitation'
                },
                inviteUserByCode: {
                    label: '邀请码',
                    name: 'invite_code'
                },
                urlParams: {
                    label: 'url地址参数',
                    name: 'urlparams'
                },
                models: {
                    username: null,
                    password: null,
                    rePassword: null,
                    phone: null,
                    phoneCode: null,
                    inviteCode: null,
                    urlParams: null,
                },
                current_date: (new Date()).getTime(),
                inviteUsername: null,
                inviteUrlCode: $routeParams['invited']
            },
            urlParams = JSON.stringify($location.search()),
            stepConf = [true, false, false];

        if($location.path() == '/register' && $location.search()['puthin'] != null){
            $location.path('/generalize');
            $window.location.href=$location.absUrl();
            $window.location.reload();
        }
        $scope.stepConf = stepConf;

        if(urlParams){
            formControls.models.urlParams = urlParams;
        }

        // refresh image code
        $scope.reload_vcode = function reload_vcode(){
            $scope.formControls.current_date = (new Date()).getTime();
        }

        //get the invited user by invited url
        if(formControls.inviteUrlCode){
            var conf = configFactory(['getInvitedUser'], {params: {invite_code: formControls.inviteUrlCode}});
            requestProxy(conf)
                .success(function(data){
                    formControls.inviteUsername = data.username;
                });
        }

        // get the invited user by code
        $scope.getInvitedUser = function(){
            if(formControls.models.inviteCode){
                var conf = configFactory(['getInvitedUserByCode'], {params: {invite_code: formControls.models.inviteCode}});
                requestProxy(conf)
                    .success(function(data){
                        formControls.inviteUsername = data.username;
                    }).error(function(data){
                        if(!formControls.inviteUrlCode)
                            formControls.inviteUsername = null;
                    });
            } else if(!formControls.models.inviteCode && !formControls.inviteUrlCode) {
                formControls.inviteUsername = null;
            }
        }
        $scope.getInvitedUser();

        //set the callback function
        formControls.conf['success'] = function(){
            $scope.goStep(2);
            for(var i in formControls.models)
                formControls.models[i] = null;
            requestProxy({keyName: 'getUser'})
                .success(function(data){
                    $rootScope.CURRENT_USER_ID = data.id;
                    $rootScope.CURRENT_USER_NAME = data.username;
                });
        }

        $scope.formControls = formControls;

        //set a function to change the step
        $scope.goStep = function(index){
            for(var i in stepConf)
                stepConf[i] = false;
            stepConf[index] = true;
        }
    }]);

})
