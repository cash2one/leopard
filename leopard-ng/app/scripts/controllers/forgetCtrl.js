define(['app', 'service'], function (app) {

    'use strict';

    app.controller('forgetCtrl', ['requestProxy', 'messagePrompt', '$scope', '$location'
        , function(requestProxy, messagePrompt, $scope, $location){

        var formControls = {
                conf: {
                    keyName: 'setBackPass' //this is the config's name in 'config'
                },
                username: {
                    label: '用户名',
                    name: 'user_info',
                    pattern: '/^[a-zA-Z0-9\\u4E00-\\u9FA5]{3,32}$/',
                    warning: '用户名应由3-32位数字、英文或中文组成 !',
                    keyName: 'retrievePasswordCode',
                    require: true
                },
                phoneCode: {
                    label: '短信验证码',
                    name: 'phone_code',
                    require: true
                },
                password: {
                    label: '新密码',
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
                models: {
                    username: null,
                    phoneCode: null,
                    password: null,
                    rePassword: null
                },
                current_date: (new Date()).getTime(),

            };

        // refresh image code
        $scope.reload_vcode = function reload_vcode(){
            $scope.formControls.current_date = (new Date()).getTime();
        }

        //set the callback function
        formControls.conf['success'] = function(data){
            for(var i in formControls.models)
                formControls.models[i] = null;
            messagePrompt.success(data.message);
            $location.path('/login');
        }
        formControls.conf['error'] = function(data){
            formControls.models.password = null;
            formControls.models.rePassword = null;
        }

        $scope.formControls = formControls;
    }]);

})
