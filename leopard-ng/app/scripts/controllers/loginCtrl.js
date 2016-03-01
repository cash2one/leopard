define(['app', 'angularCookie', 'service'], function (app) {

    'use strict';

    app.controller('loginCtrl', ['requestProxy', 'messagePrompt'
        , '$scope', '$cookies', '$location', '$rootScope'
        , function(requestProxy, messagePrompt, $scope, $cookies
            , $location, $rootScope){

        var formControls = {
                conf: {
                    keyName: 'login' //this is the config's name in 'config'
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
                rememberMe: false,
                name: null,
                pass: null,
                vcode: null,
                current_date: (new Date()).getTime()
            };
        //set the callback function
        formControls.conf['success'] = function(data){
            //set the remember name
            if(formControls.rememberMe)
                $cookies['remember_name'] = formControls.name;
            else
                $cookies['remember_name'] = '';

            $rootScope.CURRENT_USER_ID = data.user_id;

            messagePrompt.success('登录成功 !');
            var p = $location.search()['redirectURL'];
            if(p)
                $location.search('redirectURL', null);
            $location.path(p?decodeURIComponent(p): '/account/dashboard');

            requestProxy({keyName: 'getUser'})
                .success(function(data){
                    $rootScope.CURRENT_USER_NAME = data.username;
                });
        }

        formControls.conf['error'] = function(data){
            formControls.pass = null;
            $scope.formControls.current_date = (new Date()).getTime();
        }

        $scope.reload_vcode = function reload_vcode(){
            $scope.formControls.current_date = (new Date()).getTime();
        }

        $scope.formControls = formControls;

        //get the cookies
        formControls.rememberMe = !!$cookies['remember_name'];
        if(formControls.rememberMe)
            formControls.name = $cookies['remember_name'];
    }]);

})
